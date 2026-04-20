const STORAGE_KEY = "busManagementSystemState";

const defaultState = {
  activeBusId: "bus-1",
  buses: [
    {
      id: "bus-1",
      name: "Campus Express",
      seats: 24,
      bookedSeats: [2, 7, 11],
      bookings: [
        {
          id: "booking-1",
          name: "Rahul",
          seatNumber: 2,
          createdAt: "2026-04-20T08:30:00.000Z",
        },
        {
          id: "booking-2",
          name: "Anjali",
          seatNumber: 7,
          createdAt: "2026-04-20T09:15:00.000Z",
        },
        {
          id: "booking-3",
          name: "Karan",
          seatNumber: 11,
          createdAt: "2026-04-20T10:00:00.000Z",
        },
      ],
    },
  ],
};

let state = loadState();
let selectedSeatNumber = null;

initializeApp();

function initializeApp() {
  ensureActiveBus();
  setupActiveNav();

  const page = document.body.dataset.page;

  if (page === "home") {
    initializeBookingPage();
  }

  if (page === "admin") {
    initializeAdminPage();
  }

  if (page === "login") {
    initializeLoginPage();
  }
}

function initializeBookingPage() {
  const busSelect = document.getElementById("booking-bus-select");
  const bookingForm = document.getElementById("booking-form");

  renderBusOptions(busSelect);
  renderBookingPage();

  busSelect.addEventListener("change", (event) => {
    state.activeBusId = event.target.value;
    selectedSeatNumber = null;
    saveState();
    renderBookingPage();
  });

  bookingForm.addEventListener("submit", handleBookingSubmit);
}

function initializeAdminPage() {
  const addBusForm = document.getElementById("add-bus-form");
  const resetSeatsBtn = document.getElementById("reset-seats-btn");

  renderAdminPage();

  addBusForm.addEventListener("submit", handleAddBus);
  resetSeatsBtn.addEventListener("click", handleResetSeats);
}

function initializeLoginPage() {
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");

  loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    setMessage(
      loginMessage,
      "Login UI is ready. Backend authentication can be connected here.",
      "success"
    );
  });
}

function loadState() {
  const storedState = localStorage.getItem(STORAGE_KEY);

  if (!storedState) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultState));
    return cloneDefaultState();
  }

  try {
    const parsedState = JSON.parse(storedState);

    if (!Array.isArray(parsedState.buses) || !parsedState.buses.length) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultState));
      return cloneDefaultState();
    }

    return parsedState;
  } catch (error) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultState));
    return cloneDefaultState();
  }
}

function cloneDefaultState() {
  return JSON.parse(JSON.stringify(defaultState));
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function ensureActiveBus() {
  const exists = state.buses.some((bus) => bus.id === state.activeBusId);

  if (!exists) {
    state.activeBusId = state.buses[0].id;
    saveState();
  }
}

function getActiveBus() {
  return state.buses.find((bus) => bus.id === state.activeBusId) || state.buses[0];
}

function getAllBookings() {
  return state.buses.flatMap((bus) =>
    bus.bookings.map((booking) => ({
      ...booking,
      busName: bus.name,
    }))
  );
}

function renderBusOptions(selectElement) {
  if (!selectElement) {
    return;
  }

  selectElement.innerHTML = state.buses
    .map(
      (bus) => `
        <option value="${bus.id}" ${bus.id === state.activeBusId ? "selected" : ""}>
          ${bus.name}
        </option>
      `
    )
    .join("");
}

function renderBookingPage() {
  const activeBus = getActiveBus();
  const bookedCount = activeBus.bookedSeats.length;
  const availableCount = activeBus.seats - bookedCount;

  setText("hero-bus-name", activeBus.name);
  setText("hero-available-count", String(availableCount));
  setText("active-bus-label", activeBus.name);
  setText("active-bus-capacity", `${activeBus.seats} seats`);
  setText("booked-count", String(bookedCount));

  renderSelectedSeat();
  renderSeatGrid();
}

function renderSelectedSeat() {
  const selectedSeatDisplay = document.getElementById("selected-seat-display");
  const seatInput = document.getElementById("seat-number");

  if (!selectedSeatDisplay || !seatInput) {
    return;
  }

  const seatText = selectedSeatNumber ? `Seat ${selectedSeatNumber}` : "None";
  selectedSeatDisplay.textContent = seatText;
  seatInput.value = selectedSeatNumber || "";
}

function renderSeatGrid() {
  const activeBus = getActiveBus();
  const seatGrid = document.getElementById("seat-grid");

  if (!seatGrid) {
    return;
  }

  const items = [];

  for (let seatNumber = 1; seatNumber <= activeBus.seats; seatNumber += 1) {
    items.push(createSeatMarkup(activeBus, seatNumber));

    if (seatNumber % 4 === 2) {
      items.push('<span class="seat" data-position="aisle" aria-hidden="true"></span>');
    }
  }

  seatGrid.innerHTML = items.join("");
  seatGrid.querySelectorAll("[data-seat-number]").forEach((seatButton) => {
    seatButton.addEventListener("click", handleSeatSelection);
  });
}

function createSeatMarkup(activeBus, seatNumber) {
  const isBooked = activeBus.bookedSeats.includes(seatNumber);
  const isSelected = selectedSeatNumber === seatNumber;
  const seatClass = isBooked ? "booked" : isSelected ? "selected" : "available";

  return `
    <button
      class="seat ${seatClass}"
      type="button"
      data-seat-number="${seatNumber}"
      ${isBooked ? "disabled" : ""}
      aria-label="Seat ${seatNumber}"
    >
      ${seatNumber}
    </button>
  `;
}

function handleSeatSelection(event) {
  const activeBus = getActiveBus();
  const seatNumber = Number(event.currentTarget.dataset.seatNumber);
  const bookingMessage = document.getElementById("booking-message");

  if (activeBus.bookedSeats.includes(seatNumber)) {
    setMessage(bookingMessage, "This seat is already booked.", "error");
    return;
  }

  selectedSeatNumber = selectedSeatNumber === seatNumber ? null : seatNumber;
  clearMessage(bookingMessage);
  renderSelectedSeat();
  renderSeatGrid();
}

function handleBookingSubmit(event) {
  event.preventDefault();

  const activeBus = getActiveBus();
  const nameInput = document.getElementById("passenger-name");
  const bookingMessage = document.getElementById("booking-message");
  const passengerName = nameInput.value.trim();

  if (!passengerName) {
    setMessage(bookingMessage, "Please enter your name.", "error");
    return;
  }

  if (!selectedSeatNumber) {
    setMessage(bookingMessage, "Please select a seat.", "error");
    return;
  }

  if (activeBus.bookedSeats.includes(selectedSeatNumber)) {
    selectedSeatNumber = null;
    renderBookingPage();
    setMessage(bookingMessage, "This seat was already booked. Select another seat.", "error");
    return;
  }

  activeBus.bookedSeats.push(selectedSeatNumber);
  activeBus.bookedSeats.sort((a, b) => a - b);
  activeBus.bookings.push({
    id: `booking-${Date.now()}`,
    name: passengerName,
    seatNumber: selectedSeatNumber,
    createdAt: new Date().toISOString(),
  });

  saveState();

  const bookedSeat = selectedSeatNumber;
  selectedSeatNumber = null;

  event.target.reset();
  renderBookingPage();
  setMessage(bookingMessage, `Seat ${bookedSeat} booked successfully for ${passengerName}.`, "success");
  window.alert(`Booking confirmed for ${passengerName}. Seat ${bookedSeat} reserved.`);
}

function renderAdminPage() {
  const allBookings = getAllBookings();
  const totalBookedSeats = state.buses.reduce((sum, bus) => sum + bus.bookedSeats.length, 0);

  setText("admin-total-buses", String(state.buses.length));
  setText("admin-total-bookings", String(allBookings.length));
  setText("admin-total-seats-booked", String(totalBookedSeats));

  renderBusList();
  renderBookingList();
}

function renderBusList() {
  const busList = document.getElementById("bus-list");

  if (!busList) {
    return;
  }

  if (!state.buses.length) {
    busList.innerHTML = '<div class="empty-state">No buses available.</div>';
    return;
  }

  busList.innerHTML = state.buses
    .map(
      (bus) => `
        <article class="list-item">
          <strong>${bus.name}</strong>
          <p>Total Seats: ${bus.seats}</p>
          <p>Booked Seats: ${bus.bookedSeats.length}</p>
        </article>
      `
    )
    .join("");
}

function renderBookingList() {
  const bookingList = document.getElementById("booking-list");
  const allBookings = getAllBookings();

  if (!bookingList) {
    return;
  }

  if (!allBookings.length) {
    bookingList.innerHTML = '<div class="empty-state">No bookings found.</div>';
    return;
  }

  bookingList.innerHTML = allBookings
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .map(
      (booking) => `
        <article class="list-item">
          <strong>${booking.name}</strong>
          <p>Bus: ${booking.busName}</p>
          <p>Seat Number: ${booking.seatNumber}</p>
          <p>${formatDate(booking.createdAt)}</p>
        </article>
      `
    )
    .join("");
}

function handleAddBus(event) {
  event.preventDefault();

  const busNameInput = document.getElementById("bus-name");
  const seatCountInput = document.getElementById("bus-seat-count");
  const adminMessage = document.getElementById("admin-message");
  const busName = busNameInput.value.trim();
  const seatCount = Number(seatCountInput.value);

  if (!busName || Number.isNaN(seatCount)) {
    setMessage(adminMessage, "Please fill in both bus name and total seats.", "error");
    return;
  }

  if (seatCount < 8 || seatCount > 60) {
    setMessage(adminMessage, "Seat count must be between 8 and 60.", "error");
    return;
  }

  const newBus = {
    id: `bus-${Date.now()}`,
    name: busName,
    seats: seatCount,
    bookedSeats: [],
    bookings: [],
  };

  state.buses.push(newBus);
  state.activeBusId = newBus.id;
  saveState();

  event.target.reset();
  renderAdminPage();
  setMessage(adminMessage, `${busName} added successfully.`, "success");
}

function handleResetSeats() {
  const adminMessage = document.getElementById("admin-message");

  state.buses = state.buses.map((bus) => ({
    ...bus,
    bookedSeats: [],
    bookings: [],
  }));

  saveState();
  renderAdminPage();
  setMessage(adminMessage, "All seat bookings have been reset.", "success");
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function setupActiveNav() {
  const page = document.body.dataset.page;
  const navLinks = document.querySelectorAll(".nav-links a");

  navLinks.forEach((link) => {
    link.classList.remove("active");

    if (
      (page === "home" && link.getAttribute("href") === "index.html") ||
      (page === "login" && link.getAttribute("href") === "login.html")
    ) {
      link.classList.add("active");
    }
  });
}

function setText(id, value) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

function setMessage(element, message, type) {
  if (!element) {
    return;
  }

  element.textContent = message;
  element.className = `status-message ${type}`;
}

function clearMessage(element) {
  if (!element) {
    return;
  }

  element.textContent = "";
  element.className = "status-message";
}
