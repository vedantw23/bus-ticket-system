from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from flask import Flask, flash, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = os.getenv("BUSMS_SECRET_KEY", "os-project-bus-management-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "bookings.json"
LEGACY_DATA_FILE = BASE_DIR / "bookings.json"
ADMIN_USERNAME = os.getenv("BUSMS_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("BUSMS_ADMIN_PASSWORD", "123")

# Global mutex lock used by every booking thread.
# This is the core synchronization primitive for the OS project.
seat_lock = Lock()

OFFICIAL_OPERATOR_CATALOG = [
    {
        "id": "bus-1",
        "name": "Shivneri",
        "state_name": "Maharashtra",
        "service_scope": "Premium Intercity Service",
        "source_label": "MSRTC Shivneri Service",
        "source_url": "https://npublic.msrtcors.com/view/secure/reservation.xhtml",
    },
    {
        "id": "bus-2",
        "name": "Vayu Vajra",
        "state_name": "Karnataka",
        "service_scope": "Airport Bus Service",
        "source_label": "BMTC Airport Service",
        "source_url": "https://mybmtc.karnataka.gov.in/new-page/Airport+Vayu+vajra+Services/en",
    },
    {
        "id": "bus-3",
        "name": "Vajra",
        "state_name": "Karnataka",
        "service_scope": "AC City Service",
        "source_label": "BMTC Vajra Service",
        "source_url": "https://en.wikipedia.org/wiki/Vajra_Bus%2C_BMTC",
    },
    {
        "id": "bus-4",
        "name": "Airavat",
        "state_name": "Karnataka",
        "service_scope": "Luxury Coach Service",
        "source_label": "KSRTC Airavat Service",
        "source_url": "https://en.wikipedia.org/wiki/Airavat_Club_Class",
    },
    {
        "id": "bus-5",
        "name": "Flybus",
        "state_name": "Karnataka",
        "service_scope": "Airport Connector",
        "source_label": "KSRTC Flybus Service",
        "source_url": "https://en.wikipedia.org/wiki/Flybus",
    },
    {
        "id": "bus-6",
        "name": "Purple",
        "state_name": "Maharashtra",
        "service_scope": "Private Coach Operator",
        "source_label": "Purple Bus",
        "source_url": "https://purplebus.in/",
    },
    {
        "id": "bus-7",
        "name": "redBus",
        "state_name": "India",
        "service_scope": "Bus Booking Platform",
        "source_label": "redBus India",
        "source_url": "https://www.redbus.in/info/aboutus",
    },
    {
        "id": "bus-8",
        "name": "BEST",
        "state_name": "Maharashtra",
        "service_scope": "Mumbai Local Bus",
        "source_label": "Official BEST",
        "source_url": "https://www.bestundertaking.com/",
    },
    {
        "id": "bus-9",
        "name": "DTC Red Bus",
        "state_name": "Delhi",
        "service_scope": "City Bus",
        "source_label": "Official DTC",
        "source_url": "https://dtc.delhi.gov.in/",
    },
    {
        "id": "bus-10",
        "name": "MTC Chennai Bus",
        "state_name": "Tamil Nadu",
        "service_scope": "City Bus",
        "source_label": "Official MTC Chennai",
        "source_url": "https://mtcbus.tn.gov.in/",
    },
    {
        "id": "bus-11",
        "name": "CTU Local Bus",
        "state_name": "Chandigarh",
        "service_scope": "City and Intercity Bus",
        "source_label": "Official CTU",
        "source_url": "https://chdctu.gov.in/",
    },
    {
        "id": "bus-12",
        "name": "JKRTC Volvo",
        "state_name": "Jammu & Kashmir",
        "service_scope": "Intercity Coach",
        "source_label": "Official JKRTC",
        "source_url": "https://www.jksrtc.co.in/",
    },
    {
        "id": "bus-13",
        "name": "Orange Travels",
        "state_name": "Telangana",
        "service_scope": "Private Sleeper Coach",
        "source_label": "Popular Private Operator",
        "source_url": "",
    },
]

OFFICIAL_OPERATOR_LOOKUP = {
    operator["id"]: operator for operator in OFFICIAL_OPERATOR_CATALOG
}

LEGACY_NAME_ALIASES = {
    "campus express": "bus-1",
    "shivneri": "bus-1",
    "karnataka state road transport corporation (ksrtc)": "bus-4",
    "andhra pradesh state road transport corporation (apsrtc)": "bus-13",
    "telangana state road transport corporation (tgsrtc)": "bus-13",
    "maharashtra state road transport corporation (msrtc)": "bus-1",
    "rajasthan state road transport corporation (rsrtc)": "bus-6",
    "gujarat state road transport corporation (gsrtc)": "bus-6",
    "odisha state road transport corporation (osrtc)": "bus-7",
    "delhi transport corporation (dtc)": "bus-9",
    "metropolitan transport corporation (chennai) ltd (mtc)": "bus-10",
    "assam state transport corporation (astc)": "bus-11",
    "chandigarh transport undertaking (ctu)": "bus-11",
    "jammu & kashmir road transport corporation (jkrtc)": "bus-12",
    "brihanmumbai electric supply & transport undertaking (best)": "bus-8",
}


def create_bus(
    bus_id: str,
    name: str,
    total_seats: int,
    state_name: str,
    service_scope: str,
    source_label: str,
    source_url: str,
    preset_bookings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one bus record with an in-memory seat array."""
    seat_status = [0] * total_seats
    bookings: list[dict[str, Any]] = []

    for booking in preset_bookings or []:
        seat_number = int(booking["seat_number"])
        if 1 <= seat_number <= total_seats and seat_status[seat_number - 1] == 0:
            seat_status[seat_number - 1] = 1
            bookings.append(
                {
                    "name": booking["name"],
                    "seat_number": seat_number,
                    "booked_at": booking["booked_at"],
                }
            )

    return {
        "id": bus_id,
        "name": name,
        "state_name": state_name,
        "service_scope": service_scope,
        "source_label": source_label,
        "source_url": source_url,
        "total_seats": total_seats,
        "seat_status": seat_status,
        "bookings": bookings,
    }


def default_bus_store() -> dict[str, dict[str, Any]]:
    """Initial in-memory data used when no JSON file exists yet.

    The operator names below are based on current public transport corporation
    names from official Indian transport sites.
    """
    buses = [
        create_bus(
            bus_id="bus-1",
            name="Karnataka State Road Transport Corporation (KSRTC)",
            total_seats=24,
            state_name="Karnataka",
            service_scope="State RTC",
            source_label="Official KSRTC",
            source_url="https://www.ksrtc.in/",
            preset_bookings=[
                {"name": "Rahul", "seat_number": 2, "booked_at": "2026-04-20 10:00:00"},
                {"name": "Anjali", "seat_number": 7, "booked_at": "2026-04-20 10:05:00"},
            ],
        ),
        create_bus(
            bus_id="bus-2",
            name="Andhra Pradesh State Road Transport Corporation (APSRTC)",
            total_seats=28,
            state_name="Andhra Pradesh",
            service_scope="State RTC",
            source_label="Official APSRTC",
            source_url="https://apsrtc.ap.gov.in/",
            preset_bookings=[
                {"name": "Vikram", "seat_number": 4, "booked_at": "2026-04-20 10:10:00"},
            ],
        ),
        create_bus(
            bus_id="bus-3",
            name="Telangana State Road Transport Corporation (TGSRTC)",
            total_seats=32,
            state_name="Telangana",
            service_scope="State RTC",
            source_label="Official TGSRTC",
            source_url="https://www.tgsrtc.telangana.gov.in/",
            preset_bookings=[
                {"name": "Sneha", "seat_number": 5, "booked_at": "2026-04-20 10:20:00"},
                {"name": "Aman", "seat_number": 12, "booked_at": "2026-04-20 10:22:00"},
            ],
        ),
        create_bus(
            bus_id="bus-4",
            name="Maharashtra State Road Transport Corporation (MSRTC)",
            total_seats=32,
            state_name="Maharashtra",
            service_scope="State RTC",
            source_label="Official MSRTC",
            source_url="https://npublic.msrtcors.com/view/secure/reservation.xhtml",
            preset_bookings=[
                {"name": "Yashraj Jangid", "seat_number": 3, "booked_at": "2026-04-20 19:26:58"},
            ],
        ),
        create_bus(
            bus_id="bus-5",
            name="Rajasthan State Road Transport Corporation (RSRTC)",
            total_seats=30,
            state_name="Rajasthan",
            service_scope="State RTC",
            source_label="Official RSRTC",
            source_url="https://transport.rajasthan.gov.in/rsrtc",
        ),
        create_bus(
            bus_id="bus-6",
            name="Gujarat State Road Transport Corporation (GSRTC)",
            total_seats=30,
            state_name="Gujarat",
            service_scope="State RTC",
            source_label="Official GSRTC",
            source_url="https://www.gsrtc.in/site/",
        ),
        create_bus(
            bus_id="bus-7",
            name="Odisha State Road Transport Corporation (OSRTC)",
            total_seats=30,
            state_name="Odisha",
            service_scope="State RTC",
            source_label="Official OSRTC",
            source_url="https://www.osrtc.in/busindia_OSRTC.jsp",
        ),
        create_bus(
            bus_id="bus-8",
            name="Delhi Transport Corporation (DTC)",
            total_seats=26,
            state_name="Delhi",
            service_scope="City Bus",
            source_label="Official DTC",
            source_url="https://dtc.delhi.gov.in/",
        ),
        create_bus(
            bus_id="bus-9",
            name="Metropolitan Transport Corporation (Chennai) Ltd (MTC)",
            total_seats=26,
            state_name="Tamil Nadu",
            service_scope="City Bus",
            source_label="Official MTC Chennai",
            source_url="https://mtcbus.tn.gov.in/",
        ),
        create_bus(
            bus_id="bus-10",
            name="Assam State Transport Corporation (ASTC)",
            total_seats=26,
            state_name="Assam",
            service_scope="State RTC",
            source_label="Official ASTC",
            source_url="https://astc.assam.gov.in/",
        ),
        create_bus(
            bus_id="bus-11",
            name="Chandigarh Transport Undertaking (CTU)",
            total_seats=24,
            state_name="Chandigarh",
            service_scope="City and Intercity Bus",
            source_label="Official CTU",
            source_url="https://chdctu.gov.in/",
        ),
        create_bus(
            bus_id="bus-12",
            name="Jammu & Kashmir Road Transport Corporation (JKRTC)",
            total_seats=28,
            state_name="Jammu & Kashmir",
            service_scope="UT RTC",
            source_label="Official JKRTC",
            source_url="https://www.jksrtc.co.in/",
        ),
        create_bus(
            bus_id="bus-13",
            name="Brihanmumbai Electric Supply & Transport Undertaking (BEST)",
            total_seats=24,
            state_name="Maharashtra",
            service_scope="City Bus",
            source_label="Official BEST",
            source_url="https://www.bestundertaking.com/",
        ),
    ]
    return {bus["id"]: bus for bus in buses}


def normalize_loaded_state(raw_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Convert JSON data back into the in-memory structure used by Flask."""
    buses = raw_data.get("buses", [])
    normalized: dict[str, dict[str, Any]] = {}

    for index, raw_bus in enumerate(buses, start=1):
        bus_id = str(raw_bus.get("id") or f"bus-{index}")
        name = str(raw_bus.get("name") or f"Bus {index}")
        state_name = str(raw_bus.get("state_name") or "India")
        service_scope = str(raw_bus.get("service_scope") or "Operator")
        source_label = str(raw_bus.get("source_label") or "Configured Backend Source")
        source_url = str(raw_bus.get("source_url") or "")
        total_seats = int(raw_bus.get("total_seats") or len(raw_bus.get("seat_status", [])) or 20)
        raw_seat_status = raw_bus.get("seat_status", [])
        seat_status = [1 if int(value) else 0 for value in raw_seat_status][:total_seats]

        if len(seat_status) < total_seats:
            seat_status.extend([0] * (total_seats - len(seat_status)))

        bookings: list[dict[str, Any]] = []
        for raw_booking in raw_bus.get("bookings", []):
            seat_number = int(raw_booking.get("seat_number", 0))
            if 1 <= seat_number <= total_seats:
                seat_status[seat_number - 1] = 1
                bookings.append(
                    {
                        "name": str(raw_booking.get("name", "Unknown")),
                        "seat_number": seat_number,
                        "booked_at": str(raw_booking.get("booked_at", "")),
                    }
                )

        alias_operator_id = LEGACY_NAME_ALIASES.get(name.strip().lower())
        official_operator = OFFICIAL_OPERATOR_LOOKUP.get(bus_id)
        if official_operator is None and alias_operator_id:
            official_operator = OFFICIAL_OPERATOR_LOOKUP.get(alias_operator_id)

        if official_operator:
            bus_id = official_operator["id"]
            name = official_operator["name"]
            state_name = official_operator["state_name"]
            service_scope = official_operator["service_scope"]
            source_label = official_operator["source_label"]
            source_url = official_operator["source_url"]

        normalized[bus_id] = {
            "id": bus_id,
            "name": name,
            "state_name": state_name,
            "service_scope": service_scope,
            "source_label": source_label,
            "source_url": source_url,
            "total_seats": total_seats,
            "seat_status": seat_status,
            "bookings": bookings,
        }

    if not normalized:
        return default_bus_store()

    for operator in OFFICIAL_OPERATOR_CATALOG:
        if operator["id"] not in normalized:
            normalized[operator["id"]] = create_bus(
                bus_id=operator["id"],
                name=operator["name"],
                total_seats=24,
                state_name=operator["state_name"],
                service_scope=operator["service_scope"],
                source_label=operator["source_label"],
                source_url=operator["source_url"],
            )

    ordered_bus_ids = [operator["id"] for operator in OFFICIAL_OPERATOR_CATALOG]
    return {bus_id: normalized[bus_id] for bus_id in ordered_bus_ids if bus_id in normalized}


def load_bus_store() -> dict[str, dict[str, Any]]:
    """Load buses from JSON if available, otherwise create default data."""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as data_file:
                return normalize_loaded_state(json.load(data_file))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    if LEGACY_DATA_FILE.exists():
        try:
            with LEGACY_DATA_FILE.open("r", encoding="utf-8") as data_file:
                migrated_state = normalize_loaded_state(json.load(data_file))
                write_state_to_disk(migrated_state)
                return migrated_state
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    default_state = default_bus_store()
    write_state_to_disk(default_state)
    return default_state


def serializable_state(bus_store: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Prepare the in-memory state for JSON storage."""
    return {"buses": list(bus_store.values())}


def write_state_to_disk(bus_store: dict[str, dict[str, Any]]) -> None:
    """Persist bookings to JSON for simple academic demonstration."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as data_file:
        json.dump(serializable_state(bus_store), data_file, indent=2)


BUS_STORE = load_bus_store()


def login_required(view_function):
    """Protect admin pages using a simple Flask session flag."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in as admin first.", "error")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def snapshot_buses() -> list[dict[str, Any]]:
    """Return a deep copy so templates never read shared mutable state directly."""
    seat_lock.acquire()
    try:
        return json.loads(json.dumps(list(BUS_STORE.values())))
    finally:
        seat_lock.release()


def find_selected_bus(buses: list[dict[str, Any]], requested_bus_id: str | None) -> dict[str, Any]:
    """Pick the bus that should be shown on the current page."""
    if requested_bus_id:
        for bus in buses:
            if bus["id"] == requested_bus_id:
                return bus
    return buses[0]


def next_bus_id() -> str:
    """Generate a simple incremental bus id."""
    existing_numbers = []
    for bus_id in BUS_STORE:
        try:
            existing_numbers.append(int(bus_id.split("-")[-1]))
        except ValueError:
            continue
    return f"bus-{max(existing_numbers, default=0) + 1}"


def booking_worker(bus_id: str, passenger_name: str, seat_number: int, result: dict[str, Any]) -> None:
    """Thread target for seat booking.

    Each request creates a worker thread. The shared lock prevents two threads
    from booking the same seat at the same time.
    """
    try:
        with seat_lock:
            bus = BUS_STORE.get(bus_id)

            if bus is None:
                result["success"] = False
                result["message"] = "Selected bus does not exist."
                return

            if seat_number < 1 or seat_number > bus["total_seats"]:
                result["success"] = False
                result["message"] = "Invalid seat number."
                return

            if bus["seat_status"][seat_number - 1] == 1:
                print(f"Seat {seat_number} already booked")
                result["success"] = False
                result["message"] = f"Seat {seat_number} is already booked."
                return

            bus["seat_status"][seat_number - 1] = 1
            bus["bookings"].append(
                {
                    "name": passenger_name,
                    "seat_number": seat_number,
                    "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            try:
                write_state_to_disk(BUS_STORE)
            except OSError as exc:
                # Keep the booking visible even if persistence is temporarily unavailable.
                print(f"Warning: booking saved in memory but could not be written to disk: {exc}")
                result["success"] = True
                result["message"] = (
                    f"Seat {seat_number} booked successfully for {passenger_name}, "
                    f"but the booking could not be written to disk: {exc}"
                )
                return

            print(f"Seat {seat_number} booked by {passenger_name}")
            result["success"] = True
            result["message"] = f"Seat {seat_number} booked successfully for {passenger_name}."
    except Exception as exc:  # pragma: no cover - defensive safety for thread failures
        print("Booking worker failed with an unexpected error:")
        print(traceback.format_exc())
        result["success"] = False
        result["message"] = f"Unexpected booking error: {exc}"


@app.route("/")
def home():
    buses = snapshot_buses()
    current_bus = find_selected_bus(buses, request.args.get("bus_id"))
    booked_count = sum(current_bus["seat_status"])
    available_count = current_bus["total_seats"] - booked_count

    return render_template(
        "index.html",
        buses=buses,
        current_bus=current_bus,
        booked_count=booked_count,
        available_count=available_count,
        data_file_path=str(DATA_FILE.relative_to(BASE_DIR)),
        official_operators=OFFICIAL_OPERATOR_CATALOG,
    )


@app.route("/book", methods=["POST"])
def book_seat():
    passenger_name = request.form.get("name", "").strip()
    bus_id = request.form.get("bus_id", "").strip()
    seat_number_raw = request.form.get("seat_number", "").strip()

    if not passenger_name or not seat_number_raw:
        flash("Please enter your name and choose a seat.", "error")
        return redirect(url_for("home", bus_id=bus_id or None))

    try:
        seat_number = int(seat_number_raw)
    except ValueError:
        flash("Seat number must be numeric.", "error")
        return redirect(url_for("home", bus_id=bus_id or None))

    booking_result: dict[str, Any] = {
        "success": False,
        "message": "Unable to process the booking.",
    }

    # Thread-per-booking request for OS concurrency demonstration.
    booking_thread = Thread(
        target=booking_worker,
        args=(bus_id, passenger_name, seat_number, booking_result),
        daemon=False,
    )
    booking_thread.start()
    booking_thread.join()

    flash(
        booking_result.get("message", "Unable to process the booking."),
        "success" if booking_result.get("success") else "error",
    )
    return redirect(url_for("home", bus_id=bus_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_panel"))

        flash("Invalid admin username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Admin session cleared.", "success")
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin_panel():
    buses = snapshot_buses()
    total_bookings = sum(len(bus["bookings"]) for bus in buses)
    total_booked_seats = sum(sum(bus["seat_status"]) for bus in buses)

    return render_template(
        "admin.html",
        buses=buses,
        total_buses=len(buses),
        total_bookings=total_bookings,
        total_booked_seats=total_booked_seats,
        data_file_path=str(DATA_FILE.relative_to(BASE_DIR)),
    )


@app.route("/add_bus", methods=["POST"])
@login_required
def add_bus():
    bus_name = request.form.get("bus_name", "").strip()
    total_seats_raw = request.form.get("total_seats", "").strip()

    if not bus_name or not total_seats_raw:
        flash("Bus name and total seats are required.", "error")
        return redirect(url_for("admin_panel"))

    try:
        total_seats = int(total_seats_raw)
    except ValueError:
        flash("Total seats must be numeric.", "error")
        return redirect(url_for("admin_panel"))

    if total_seats < 8:
        flash("Please enter at least 8 seats for a bus.", "error")
        return redirect(url_for("admin_panel"))

    seat_lock.acquire()
    try:
        bus_id = next_bus_id()
        BUS_STORE[bus_id] = create_bus(
            bus_id=bus_id,
            name=bus_name,
            total_seats=total_seats,
            state_name="Custom Entry",
            service_scope="Admin Added",
            source_label="Added from Admin Panel",
            source_url="",
        )
        write_state_to_disk(BUS_STORE)
    finally:
        seat_lock.release()

    flash(f"{bus_name} added successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/reset", methods=["POST"])
@login_required
def reset_seats():
    seat_lock.acquire()
    try:
        for bus in BUS_STORE.values():
            bus["seat_status"] = [0] * bus["total_seats"]
            bus["bookings"] = []
        write_state_to_disk(BUS_STORE)
    finally:
        seat_lock.release()

    flash("All seats have been reset to available.", "success")
    return redirect(url_for("admin_panel"))


if __name__ == "__main__":
    app.run(debug=True)
