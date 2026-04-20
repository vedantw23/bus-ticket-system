document.addEventListener("DOMContentLoaded", () => {
  const seatButtons = document.querySelectorAll("#seat-grid .seat[data-seat-number]");
  const seatInput = document.getElementById("seat-number");
  const selectedSeatDisplay = document.getElementById("selected-seat-display");
  const busSelect = document.getElementById("bus-select");

  let selectedSeatButton = null;

  seatButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) {
        window.alert("This seat is already booked.");
        return;
      }

      if (selectedSeatButton) {
        selectedSeatButton.classList.remove("selected");
        selectedSeatButton.classList.add("available");
      }

      if (selectedSeatButton === button) {
        selectedSeatButton = null;
        if (seatInput) {
          seatInput.value = "";
        }
        if (selectedSeatDisplay) {
          selectedSeatDisplay.textContent = "None";
        }
        return;
      }

      selectedSeatButton = button;
      button.classList.remove("available");
      button.classList.add("selected");

      if (seatInput) {
        seatInput.value = button.dataset.seatNumber;
      }

      if (selectedSeatDisplay) {
        selectedSeatDisplay.textContent = `Seat ${button.dataset.seatNumber}`;
      }
    });
  });

  if (busSelect) {
    busSelect.addEventListener("change", () => {
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("bus_id", busSelect.value);
      nextUrl.hash = "booking";
      window.location.href = nextUrl.toString();
    });
  }
});
