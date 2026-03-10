from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db import get_db

router = APIRouter(prefix="/games", tags=["scoreboard"])

@router.get("/{game_id}/scoreboard/timeline")
def scoreboard_timeline(game_id: UUID, db: Session = Depends(get_db)):
    game_exists = db.execute(text("SELECT 1 FROM games WHERE id = :gid"), {"gid": str(game_id)}).scalar()
    if not game_exists:
        raise HTTPException(status_code=404, detail="Game not found")

    # Each row in hands represents winner vs loser with amount_won
    rows = db.execute(
        text("""
        SELECT
          h.hand_number,
          h.winner_user_id::text AS winner_id,
          h.loser_user_id::text  AS loser_id,
          COALESCE(h.amount_won, 0)::numeric(12,2) AS amount
        FROM hands h
        WHERE h.game_id = :gid
        ORDER BY h.hand_number ASC, h.created_at ASC;
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    # Return raw rows; UI can compute per-hand deltas & running totals
    return {
        "game_id": str(game_id),
        "rows": [dict(r) for r in rows],
    }

@router.get("/{game_id}/scoreboard/matrix")
def get_scoreboard_matrix(game_id: UUID, db: Session = Depends(get_db)):
    game_exists = db.execute(
        text("SELECT 1 FROM games WHERE id = :gid"),
        {"gid": str(game_id)},
    ).scalar()

    if not game_exists:
        raise HTTPException(status_code=404, detail="Game not found")

    players = db.execute(
        text("""
            SELECT u.id, u.display_name
            FROM game_players gp
            JOIN users u ON u.id = gp.user_id
            WHERE gp.game_id = :gid
            ORDER BY u.display_name
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    hands = db.execute(
        text("""
            SELECT
                h.hand_number,
                h.winner_user_id::text AS winner_user_id,
                h.loser_user_id::text AS loser_user_id,
                COALESCE(h.amount_won, 0)::numeric(12,2) AS amount_won
            FROM hands h
            WHERE h.game_id = :gid
            ORDER BY h.hand_number ASC, h.created_at ASC
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    hand_numbers = sorted({int(h["hand_number"]) for h in hands})

    player_rows = {}
    for p in players:
        player_rows[str(p["id"])] = {
            "player_id": str(p["id"]),
            "display_name": p["display_name"],
            "hands": {str(hn): 0.0 for hn in hand_numbers},
            "cumulative": 0.0,
        }

    hand_totals = {str(hn): 0.0 for hn in hand_numbers}

    for h in hands:
        hn = str(int(h["hand_number"]))
        amount = float(h["amount_won"])
        winner = h["winner_user_id"]
        loser = h["loser_user_id"]

        if winner in player_rows:
            player_rows[winner]["hands"][hn] += amount
            player_rows[winner]["cumulative"] += amount
            hand_totals[hn] += amount

        if loser in player_rows:
            player_rows[loser]["hands"][hn] -= amount
            player_rows[loser]["cumulative"] -= amount
            hand_totals[hn] -= amount

    return {
        "game_id": str(game_id),
        "hand_numbers": hand_numbers,
        "players": list(player_rows.values()),
        "hand_totals": hand_totals,
    }
@router.get("/{game_id}/scoreboard/session")
def get_scoreboard_session(game_id: UUID, db: Session = Depends(get_db)):
    game_exists = db.execute(
        text("SELECT 1 FROM games WHERE id = :gid"),
        {"gid": str(game_id)},
    ).scalar()

    if not game_exists:
        raise HTTPException(status_code=404, detail="Game not found")

    players = db.execute(
        text("""
            SELECT u.id::text AS player_id, u.display_name
            FROM game_players gp
            JOIN users u ON u.id = gp.user_id
            WHERE gp.game_id = :gid
            ORDER BY u.display_name
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    rows = db.execute(
        text("""
            SELECT
                h.id::text AS row_id,
                h.hand_number,
                h.card_number,
                h.created_at,
                h.winner_user_id::text AS winner_user_id,
                h.loser_user_id::text AS loser_user_id,
                COALESCE(h.amount_won, 0)::numeric(12,2) AS amount_won
            FROM hands h
            WHERE h.game_id = :gid
            ORDER BY h.hand_number ASC, h.card_number ASC, h.created_at ASC, h.id ASC
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    player_map = {p["player_id"]: p["display_name"] for p in players}
    player_ids = [p["player_id"] for p in players]

    # group rows by hand_number, then aggregate settlement rows by card_number
    hands_grouped = defaultdict(list)
    for r in rows:
        hands_grouped[int(r["hand_number"])].append(r)

    hands_output = []
    session_totals = {pid: 0.0 for pid in player_ids}
    hand_summary_rows = []

    for hand_number in sorted(hands_grouped.keys()):
        hand_rows = hands_grouped[hand_number]

        # card matrix for this hand
        # player -> card_number -> amount
        player_card_amounts = {
            pid: {} for pid in player_ids
        }
        hand_totals = {pid: 0.0 for pid in player_ids}
        card_totals = {}

        cards = {}

        for r in hand_rows:
            cards.setdefault(r.card_number, []).append(r)

        for card_number in sorted(cards.keys()):
            card_rows = cards[card_number]
            card_key = f"Card {card_number}"

            card_totals[card_key] = 0.0

            for r in card_rows:
                winner = r["winner_user_id"]
                loser = r["loser_user_id"]
                amount = float(r["amount_won"])

                if winner in player_card_amounts:
                    player_card_amounts[winner][card_key] = player_card_amounts[winner].get(card_key, 0.0) + amount
                    hand_totals[winner] += amount
                    session_totals[winner] += amount
                    card_totals[card_key] += amount

                if loser in player_card_amounts:
                    player_card_amounts[loser][card_key] = player_card_amounts[loser].get(card_key, 0.0) - amount
                    hand_totals[loser] -= amount
                    session_totals[loser] -= amount
                    card_totals[card_key] -= amount

        hand_player_rows = []
        for pid in player_ids:
            hand_player_rows.append({
                "player_id": pid,
                "display_name": player_map[pid],
                "cards": player_card_amounts[pid],
                "hand_total": hand_totals[pid],
            })

        hands_output.append({
            "hand_number": hand_number,
            "cards": list(card_totals.keys()),
            "players": hand_player_rows,
            "card_totals": card_totals,
            "hand_total_sum": sum(card_totals.values()),
        })

        hand_summary_rows.append({
            "hand_number": hand_number,
            "totals": {pid: hand_totals[pid] for pid in player_ids},
        })

    session_summary_players = [
        {
            "player_id": pid,
            "display_name": player_map[pid],
            "session_total": session_totals[pid],
        }
        for pid in player_ids
    ]

    return {
        "game_id": str(game_id),
        "hands": hands_output,
        "hand_summary": hand_summary_rows,
        "session_summary": session_summary_players,
    }