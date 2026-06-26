from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_conn


def _parse_depart_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_optional_date(value: Any) -> Optional[date]:
    v = str(value or "").strip()
    if not v:
        return None
    return datetime.strptime(v, "%Y-%m-%d").date()


def _dt_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _flt(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _bool(value: Any) -> bool:
    return bool(value)


def _normalize_trip_type(value: Any) -> str:
    v = str(value or "ONE_WAY").strip().upper()
    if v not in ("ONE_WAY", "ROUND_TRIP"):
        raise ValueError("Invalid search.trip_type. Allowed: ONE_WAY, ROUND_TRIP")
    return v


def _fetch_search_rows(
    *,
    from_airport: str,
    to_airport: str,
    travel_date: date,
    cabin_class: str,
    currency: str,
    preferred_airline: Optional[str],
    top_n: Optional[int],
    include_days: int,
) -> List[Dict[str, Any]]:
    start_dt = datetime.combine(travel_date - timedelta(days=include_days), datetime.min.time())
    end_dt = datetime.combine(travel_date + timedelta(days=include_days + 1), datetime.min.time())

    base_where = """
        FROM vw_flight_search_api
        WHERE departure_airport = %s
          AND arrival_airport = %s
          AND scheduled_departure >= %s
          AND scheduled_departure < %s
          AND scheduled_departure > NOW()
          AND UPPER(TRIM(flight_status)) = 'SCHEDULED'
          AND travel_class = %s
          AND currency = %s
          AND fare_is_active = 1
          AND EXISTS (
                SELECT 1
                  FROM flight f
                 WHERE f.flight_id = vw_flight_search_api.flight_id
                   AND f.is_active = 1
                   AND f.available_seats > 0
                   AND UPPER(TRIM(f.flight_status)) = 'SCHEDULED'
                   AND f.scheduled_departure > NOW()
          )
    """
    base_params: List[Any] = [
        from_airport,
        to_airport,
        start_dt,
        end_dt,
        cabin_class,
        currency,
    ]

    if preferred_airline:
        base_where += " AND airline_code = %s "
        base_params.append(preferred_airline)

    select_cols = """
        SELECT
          flight_id, flight_number, airline_code, airline_name,
          from_city, to_city,
          departure_airport, arrival_airport,
          scheduled_departure, scheduled_arrival,
          flight_status, aircraft_type, distance_km, duration_min,
          no_of_stop, layover1_airport_code, layover1_min,
          layover2_airport_code, layover2_min,
          layover3_airport_code, layover3_min,
          fare_id, travel_class, fare_family_name, fare_basis,
          refundable, changeable, baggage_allowance,
          base_fare, taxes, fees, currency,
          scheduled_departure_formatted, scheduled_arrival_formatted,
          duration_formatted, stops_formatted,
          refundable_formatted, changeable_formatted,
          total_fare_calc
    """

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if top_n is None:
                sql = select_cols + base_where + " ORDER BY scheduled_departure ASC, total_fare_calc ASC "
                cur.execute(sql, base_params)
                return list(cur.fetchall() or [])

            flight_id_sql = """
                SELECT flight_id
            """ + base_where + """
                GROUP BY flight_id
                ORDER BY MIN(scheduled_departure) ASC, MIN(total_fare_calc) ASC, flight_id ASC
                LIMIT %s
            """
            flight_id_params = list(base_params) + [top_n]
            cur.execute(flight_id_sql, flight_id_params)
            flight_id_rows = list(cur.fetchall() or [])
            selected_flight_ids = [int(r["flight_id"]) for r in flight_id_rows if r.get("flight_id") is not None]

            if not selected_flight_ids:
                return []

            placeholders = ", ".join(["%s"] * len(selected_flight_ids))
            sql = (
                select_cols
                + base_where
                + f" AND flight_id IN ({placeholders}) "
                + " ORDER BY scheduled_departure ASC, total_fare_calc ASC, flight_id ASC, fare_id ASC "
            )
            params = list(base_params) + selected_flight_ids
            cur.execute(sql, params)
            return list(cur.fetchall() or [])
    finally:
        conn.close()


def _build_flight_object(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "flight_id": r["flight_id"],
        "flight_number": r["flight_number"],
        "airline": {
            "code": r["airline_code"],
            "name": r["airline_name"],
        },
        "route": {
            "from": {
                "airport": r["departure_airport"],
                "city": r["from_city"],
            },
            "to": {
                "airport": r["arrival_airport"],
                "city": r["to_city"],
            },
        },
        "schedule": {
            "scheduled_departure": _dt_str(r["scheduled_departure"]),
            "scheduled_arrival": _dt_str(r["scheduled_arrival"]),
            "scheduled_departure_formatted": r["scheduled_departure_formatted"],
            "scheduled_arrival_formatted": r["scheduled_arrival_formatted"],
        },
        "status": r["flight_status"],
        "aircraft_type": r["aircraft_type"],
        "distance_km": r["distance_km"],
        "duration_min": r["duration_min"],
        "duration_formatted": r["duration_formatted"],
        "stops": {
            "no_of_stop": r["no_of_stop"],
            "stops_formatted": r["stops_formatted"],
            "layover1_airport_code": r["layover1_airport_code"],
            "layover1_min": r["layover1_min"],
            "layover2_airport_code": r["layover2_airport_code"],
            "layover2_min": r["layover2_min"],
            "layover3_airport_code": r["layover3_airport_code"],
            "layover3_min": r["layover3_min"],
        },
    }


def _build_fare_object(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "fare_id": r["fare_id"],
        "travel_class": r["travel_class"],
        "fare_family_name": r.get("fare_family_name") or r["fare_basis"],
        "fare_basis": r["fare_basis"],
        "refundable": _bool(r["refundable"]),
        "changeable": _bool(r["changeable"]),
        "baggage_allowance": r["baggage_allowance"],
        "price": {
            "base_fare": _flt(r["base_fare"]),
            "taxes": _flt(r["taxes"]),
            "fees": _flt(r["fees"]),
            "total": _flt(r["total_fare_calc"]),
            "currency": r["currency"],
        },
        "flags": {
            "refundable_formatted": r["refundable_formatted"],
            "changeable_formatted": r["changeable_formatted"],
        },
    }


def _build_flat_result_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "row_key": {
            "flight_id": r["flight_id"],
            "flight_number": r["flight_number"],
            "scheduled_departure": _dt_str(r["scheduled_departure"]),
            "fare_id": r["fare_id"],
        },
        "flight": _build_flight_object(r),
        "fare": _build_fare_object(r),
    }


def _build_fare_option(out_row: Dict[str, Any], ret_row: Dict[str, Any]) -> Dict[str, Any]:
    outbound_total = _flt(out_row["total_fare_calc"])
    return_total = _flt(ret_row["total_fare_calc"])
    total_amount = outbound_total + return_total

    out_name = str(out_row.get("fare_family_name") or out_row["fare_basis"] or "").strip()
    ret_name = str(ret_row.get("fare_family_name") or ret_row["fare_basis"] or "").strip()
    fare_family = out_name if out_name == ret_name else f"{out_name} + {ret_name}"

    return {
        "fare_combo_key": f'{out_row["flight_id"]}:{out_row["fare_id"]}__{ret_row["flight_id"]}:{ret_row["fare_id"]}',
        "outbound_fare": _build_fare_object(out_row),
        "return_fare": _build_fare_object(ret_row),
        "fare_family": fare_family,
        "total_price": {
            "base_fare": _flt(out_row["base_fare"]) + _flt(ret_row["base_fare"]),
            "taxes": _flt(out_row["taxes"]) + _flt(ret_row["taxes"]),
            "fees": _flt(out_row["fees"]) + _flt(ret_row["fees"]),
            "total": total_amount,
            "currency": out_row["currency"],
        },
        "summary_flags": {
            "refundable_formatted": (
                out_row["refundable_formatted"]
                if str(out_row["refundable_formatted"] or "") == str(ret_row["refundable_formatted"] or "")
                else f'{out_row["refundable_formatted"]} / {ret_row["refundable_formatted"]}'
            ),
            "changeable_formatted": (
                out_row["changeable_formatted"]
                if str(out_row["changeable_formatted"] or "") == str(ret_row["changeable_formatted"] or "")
                else f'{out_row["changeable_formatted"]} / {ret_row["changeable_formatted"]}'
            ),
            "baggage_allowance": (
                out_row["baggage_allowance"]
                if str(out_row["baggage_allowance"] or "") == str(ret_row["baggage_allowance"] or "")
                else f'{out_row["baggage_allowance"]} / {ret_row["baggage_allowance"]}'
            ),
        },
        "selection": {
            "outbound_flight_id": out_row["flight_id"],
            "outbound_fare_id": out_row["fare_id"],
            "return_flight_id": ret_row["flight_id"],
            "return_fare_id": ret_row["fare_id"],
        },
    }


def _group_rows_by_flight(rows: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    flight_row_index: Dict[int, Dict[str, Any]] = {}

    for r in rows:
        fid = int(r["flight_id"])
        grouped.setdefault(fid, []).append(r)
        flight_row_index.setdefault(fid, r)

    ordered_flight_ids = sorted(
        grouped.keys(),
        key=lambda fid: (
            flight_row_index[fid]["scheduled_departure"],
            _flt(min(x["total_fare_calc"] for x in grouped[fid])),
            fid,
        ),
    )

    result: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    for fid in ordered_flight_ids:
        fare_rows = sorted(grouped[fid], key=lambda x: (_flt(x["total_fare_calc"]), x["fare_id"]))
        result.append((flight_row_index[fid], fare_rows))
    return result


def _build_round_trip_journeys(
    outbound_rows: List[Dict[str, Any]],
    return_rows: List[Dict[str, Any]],
    journey_limit: int,
) -> List[Dict[str, Any]]:
    outbound_groups = _group_rows_by_flight(outbound_rows)
    return_groups = _group_rows_by_flight(return_rows)

    journeys: List[Dict[str, Any]] = []

    for out_flight_row, out_fares in outbound_groups:
        out_arrival = out_flight_row.get("scheduled_arrival")
        for ret_flight_row, ret_fares in return_groups:
            ret_departure = ret_flight_row.get("scheduled_departure")
            if out_arrival is not None and ret_departure is not None and ret_departure <= out_arrival:
                continue

            fare_options: List[Dict[str, Any]] = []
            for out_fare_row in out_fares:
                for ret_fare_row in ret_fares:
                    fare_options.append(_build_fare_option(out_fare_row, ret_fare_row))

            fare_options.sort(
                key=lambda x: (
                    _flt(x["total_price"]["total"]),
                    str(x["fare_family"] or ""),
                    str(x["fare_combo_key"] or ""),
                )
            )

            lowest_total = fare_options[0]["total_price"]["total"] if fare_options else 0.0

            journeys.append(
                {
                    "journey_key": f'{out_flight_row["flight_id"]}__{ret_flight_row["flight_id"]}',
                    "outbound": _build_flight_object(out_flight_row),
                    "return": _build_flight_object(ret_flight_row),
                    "outbound_fares": [_build_fare_object(x) for x in out_fares],
                    "return_fares": [_build_fare_object(x) for x in ret_fares],
                    "fare_options": fare_options,
                    "lowest_total_price": {
                        "total": lowest_total,
                        "currency": out_flight_row["currency"],
                    },
                    "default_selected_fare_combo_key": fare_options[0]["fare_combo_key"] if fare_options else None,
                }
            )

    journeys.sort(
        key=lambda j: (
            _flt(j["lowest_total_price"]["total"]),
            j["outbound"]["schedule"]["scheduled_departure"],
            j["return"]["schedule"]["scheduled_departure"],
            j["journey_key"],
        )
    )

    return journeys[:journey_limit]


def search_flights(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "search" not in payload or not isinstance(payload["search"], dict):
        raise ValueError("Missing object 'search' in request")

    s = payload["search"]

    required = [
        "from_airport",
        "to_airport",
        "depart_date",
        "cabin_class",
        "currency",
        "top_n",
        "include_days",
    ]
    for k in required:
        if k not in s:
            raise ValueError(f"Missing required field search.{k}")

    trip_type = _normalize_trip_type(s.get("trip_type"))
    from_airport = str(s["from_airport"]).strip().upper()
    to_airport = str(s["to_airport"]).strip().upper()
    cabin_class = str(s["cabin_class"]).strip()
    currency = str(s["currency"]).strip().upper()
    preferred_airline = str(s.get("preferred_airline") or "").strip().upper() or None
    top_n = int(s["top_n"])
    include_days = int(s["include_days"])

    if from_airport == to_airport:
        raise ValueError("search.from_airport and search.to_airport cannot be the same")

    if top_n <= 0:
        raise ValueError("search.top_n must be greater than 0")

    if include_days < 0:
        raise ValueError("search.include_days cannot be negative")

    depart_date = _parse_depart_date(str(s["depart_date"]))
    return_date = _parse_optional_date(s.get("return_date"))

    if trip_type == "ROUND_TRIP":
        if not return_date:
            raise ValueError("Missing required field search.return_date for ROUND_TRIP")
        if return_date < depart_date:
            raise ValueError("search.return_date cannot be earlier than search.depart_date")

    if trip_type == "ONE_WAY":
        rows = _fetch_search_rows(
            from_airport=from_airport,
            to_airport=to_airport,
            travel_date=depart_date,
            cabin_class=cabin_class,
            currency=currency,
            preferred_airline=preferred_airline,
            top_n=top_n,
            include_days=include_days,
        )

        results = [_build_flat_result_row(r) for r in rows]

        return {
            "meta": {
                "provider_code": "ARS_LOCAL",
                "endpoint_type": "FLIGHT_SEARCH",
                "trip_type": "ONE_WAY",
                "result_count": len(results),
            },
            "results": results,
        }

    outbound_rows = _fetch_search_rows(
        from_airport=from_airport,
        to_airport=to_airport,
        travel_date=depart_date,
        cabin_class=cabin_class,
        currency=currency,
        preferred_airline=preferred_airline,
        top_n=None if trip_type == "ROUND_TRIP" else top_n,
        include_days=include_days,
    )

    return_rows = _fetch_search_rows(
        from_airport=to_airport,
        to_airport=from_airport,
        travel_date=return_date,
        cabin_class=cabin_class,
        currency=currency,
        preferred_airline=preferred_airline,
        top_n=None if trip_type == "ROUND_TRIP" else top_n,
        include_days=include_days,
    )

    journeys = _build_round_trip_journeys(
        outbound_rows=outbound_rows,
        return_rows=return_rows,
        journey_limit=top_n,
    )

    return {
        "meta": {
            "provider_code": "ARS_LOCAL",
            "endpoint_type": "FLIGHT_SEARCH",
            "trip_type": "ROUND_TRIP",
            "journey_count": len(journeys),
            "outbound_result_count": len(outbound_rows),
            "return_result_count": len(return_rows),
        },
        "journeys": journeys,
    }