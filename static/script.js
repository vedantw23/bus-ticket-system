document.addEventListener("DOMContentLoaded", () => {
  const seatButtons = document.querySelectorAll("#seat-grid .seat[data-seat-number]");
  const seatInput = document.getElementById("seat-number");
  const selectedSeatDisplay = document.getElementById("selected-seat-display");
  const busSelect = document.getElementById("bus-select");
  const stateFilter = document.getElementById("state-filter");
  const routeFilter = document.getElementById("route-filter");
  const applyBusFilters = document.getElementById("apply-bus-filters");
  const busFilterStatus = document.getElementById("bus-filter-status");

  let selectedSeatButton = null;

  const busOptions = busSelect
    ? Array.from(busSelect.options).map((option) => ({
        id: option.value,
        label: option.textContent.trim(),
        state: option.dataset.state || "",
        route: option.dataset.route || "",
      }))
    : [];

  const uniqueValues = (values) => Array.from(new Set(values.filter(Boolean))).sort();

  const getCurrentBus = () => {
    if (!busSelect) {
      return null;
    }

    const selectedOption = busSelect.selectedOptions[0];
    if (!selectedOption) {
      return null;
    }

    return {
      id: selectedOption.value,
      state: selectedOption.dataset.state || "",
      route: selectedOption.dataset.route || "",
    };
  };

  const renderStateOptions = (selectedState) => {
    if (!stateFilter) {
      return;
    }

    stateFilter.innerHTML = '<option value="">All states</option>';
    uniqueValues(busOptions.map((bus) => bus.state)).forEach((state) => {
      const option = document.createElement("option");
      option.value = state;
      option.textContent = state;
      stateFilter.appendChild(option);
    });

    stateFilter.value = selectedState || "";
  };

  const renderRouteOptions = (selectedState, selectedRoute) => {
    if (!routeFilter) {
      return;
    }

    const scopedRoutes = busOptions
      .filter((bus) => !selectedState || bus.state === selectedState)
      .map((bus) => bus.route);

    routeFilter.innerHTML = '<option value="">All routes</option>';
    uniqueValues(scopedRoutes).forEach((route) => {
      const option = document.createElement("option");
      option.value = route;
      option.textContent = route;
      routeFilter.appendChild(option);
    });

    routeFilter.value = uniqueValues(scopedRoutes).includes(selectedRoute) ? selectedRoute : "";
  };

  const getMatchingBuses = () => {
    if (!busOptions.length) {
      return [];
    }

    const selectedState = stateFilter ? stateFilter.value : "";
    const selectedRoute = routeFilter ? routeFilter.value : "";

    return busOptions.filter((bus) => {
      if (selectedState && bus.state !== selectedState) {
        return false;
      }

      if (selectedRoute && bus.route !== selectedRoute) {
        return false;
      }

      return true;
    });
  };

  const updateFilterStatus = () => {
    if (!busFilterStatus) {
      return;
    }

    const matches = getMatchingBuses();
    if (!matches.length) {
      busFilterStatus.textContent = "No buses match this state and route combination.";
      return;
    }

    if (matches.length === 1) {
      busFilterStatus.textContent = `${matches[0].label} is ready to open.`;
      return;
    }

    busFilterStatus.textContent = `${matches.length} buses match this combination.`;
  };

  const syncRouteFinder = () => {
    const currentBus = getCurrentBus();
    const selectedState = stateFilter && stateFilter.value ? stateFilter.value : currentBus?.state || "";
    const selectedRoute = routeFilter && routeFilter.value ? routeFilter.value : currentBus?.route || "";

    renderStateOptions(selectedState);
    renderRouteOptions(selectedState, selectedRoute);
    updateFilterStatus();
  };

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

  if (stateFilter) {
    stateFilter.addEventListener("change", () => {
      const selectedState = stateFilter.value;
      const currentRoute = routeFilter ? routeFilter.value : "";
      renderRouteOptions(selectedState, currentRoute);
      updateFilterStatus();
    });
  }

  if (routeFilter) {
    routeFilter.addEventListener("change", updateFilterStatus);
  }

  if (applyBusFilters) {
    applyBusFilters.addEventListener("click", () => {
      const matches = getMatchingBuses();
      if (!matches.length || !busSelect) {
        updateFilterStatus();
        return;
      }

      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("bus_id", matches[0].id);
      nextUrl.hash = "booking";
      window.location.href = nextUrl.toString();
    });
  }

  syncRouteFinder();
});
