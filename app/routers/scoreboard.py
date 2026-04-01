from uuid import UUID
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/games", tags=["scoreboard"])


def ensure_game_exists(game_id: UUID, db: Session):
    exists = db.execute(
        text("SELECT 1 FROM games WHERE id = :gid"),
        {"gid": str(game_id)},
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Game not found")


def get_player_rows(game_id: UUID, db: Session):
    return db.execute(
        text("""
            SELECT DISTINCT u.id::text AS player_id, u.display_name
            FROM users u
            WHERE u.id IN (
                SELECT gp.user_id
                FROM game_players gp
                WHERE gp.game_id = :gid

                UNION

                SELECT h.winner_user_id
                FROM hands h
                WHERE h.game_id = :gid
                  AND h.winner_user_id IS NOT NULL

                UNION

                SELECT h.loser_user_id
                FROM hands h
                WHERE h.game_id = :gid
                  AND h.loser_user_id IS NOT NULL
            )
            ORDER BY u.display_name
        """),
        {"gid": str(game_id)},
    ).mappings().all()


@router.get("/{game_id}/scoreboard/timeline")
def scoreboard_timeline(game_id: UUID, db: Session = Depends(get_db)):
    ensure_game_exists(game_id, db)

    rows = db.execute(
        text("""
            SELECT
                h.id::text AS row_id,
                h.hand_number,
                h.card_number,
                h.created_at,
                h.winner_user_id::text AS winner_user_id,
                h.loser_user_id::text AS loser_user_id,
                COALESCE(h.amount_won, 0)::numeric(12,2) AS amount_won,
                h.final_bid_raw,
                h.notes
            FROM hands h
            WHERE h.game_id = :gid
            ORDER BY h.hand_number ASC, h.card_number ASC, h.created_at ASC, h.id ASC
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    return {
        "game_id": str(game_id),
        "rows": [dict(r) for r in rows],
    }


@router.get("/{game_id}/scoreboard/matrix")
def get_scoreboard_matrix(game_id: UUID, db: Session = Depends(get_db)):
    ensure_game_exists(game_id, db)

    players = get_player_rows(game_id, db)

    hands = db.execute(
        text("""
            SELECT
                h.hand_number,
                h.winner_user_id::text AS winner_user_id,
                h.loser_user_id::text AS loser_user_id,
                COALESCE(h.amount_won, 0)::numeric(12,2) AS amount_won
            FROM hands h
            WHERE h.game_id = :gid
            ORDER BY h.hand_number ASC, h.created_at ASC, h.id ASC
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    hand_numbers = sorted({int(h["hand_number"]) for h in hands})

    player_rows = {}
    for p in players:
        player_rows[str(p["player_id"])] = {
            "player_id": str(p["player_id"]),
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

    hands_grouped = defaultdict(list)
    for r in rows:
        hands_grouped[int(r["hand_number"])].append(r)

    hands_output = []
    session_totals = {pid: 0.0 for pid in player_ids}
    hand_summary_rows = []
    card_roles_output = []

    for hand_number in sorted(hands_grouped.keys()):
        hand_rows = hands_grouped[hand_number]

        player_card_amounts = {pid: {} for pid in player_ids}
        hand_totals = {pid: 0.0 for pid in player_ids}
        card_totals = {}

        cards = {}
        for r in hand_rows:
            cards.setdefault(int(r["card_number"]), []).append(r)

        for card_number in sorted(cards.keys()):
            card_rows = cards[card_number]
            card_key = f"Card {card_number}"
            card_totals[card_key] = 0.0

            winners = []
            losers = []
            participants = set()

            for r in card_rows:
                winner = r["winner_user_id"]
                loser = r["loser_user_id"]
                amount = float(r["amount_won"])

                if winner:
                    winners.append(winner)
                    participants.add(winner)

                if loser:
                    losers.append(loser)
                    participants.add(loser)

                if winner in player_card_amounts:
                    player_card_amounts[winner][card_key] = (
                        player_card_amounts[winner].get(card_key, 0.0) + amount
                    )
                    hand_totals[winner] += amount
                    session_totals[winner] += amount
                    card_totals[card_key] += amount

                if loser in player_card_amounts:
                    player_card_amounts[loser][card_key] = (
                        player_card_amounts[loser].get(card_key, 0.0) - amount
                    )
                    hand_totals[loser] -= amount
                    session_totals[loser] -= amount
                    card_totals[card_key] -= amount

            unique_winners = sorted(set(winners))
            unique_losers = sorted(set(losers))

            bid_owner_user_id = None
            bid_owner_won = None

            # infer bid owner from settlement shape:
            # if one winner beats many losers -> bid owner won
            # if many winners beat one loser -> bid owner lost
            if len(unique_winners) == 1:
                bid_owner_user_id = unique_winners[0]
                bid_owner_won = True
            elif len(unique_losers) == 1:
                bid_owner_user_id = unique_losers[0]
                bid_owner_won = False

            card_roles_output.append({
                "hand_number": hand_number,
                "card_number": card_number,
                "bid_owner_user_id": bid_owner_user_id,
                "bid_owner_won": bid_owner_won,
                "amount_won": float(card_rows[0]["amount_won"]) if card_rows else 0.0,
                "participant_ids": sorted(participants),
            })

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
        "card_roles": card_roles_output,
    }