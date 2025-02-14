// Function to load podcasts from the backend
async function loadPodcasts() {

    try {

      const response = await fetch("/api/podcasts/get");
      const podcasts = await response.json();
      const podcastList = document.getElementById("podcastList");

      if (podcasts.length === 0) {
        podcastList.innerHTML = '<div class="alert alert-info">No podcasts are present.</div>';

      } else {
        console.log(podcasts);
        podcasts.forEach(podcast => {            

            const row = document.createElement("div");
            row.className = "container border p-4 mb-4";

            const podcastsTile = document.createElement("strong");
            podcastsTile.textContent = podcast.title;
            row.appendChild(podcastsTile);

            podcastList.appendChild(row);
        });
      }

    } catch (error) {
      console.error("Error loading podcasts:", error);
    }
  }

// Call loadPodcasts on page load
window.addEventListener("DOMContentLoaded", loadPodcasts);

// Handle form submission inside the modal
document.getElementById("podcastForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    // Clear any previous alerts
    document.getElementById("formAlert").innerHTML = "";

    // Gather form data
    const title = document.getElementById("title").value;
    // const description = document.getElementById("description").value;

    const data = {title};

    try {

      const response = await fetch("/api/podcasts/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (response.ok) {
        // Close the modal programmatically
        const modalEl = document.getElementById("podcastModal");
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();

        // Reset the form
        document.getElementById("podcastForm").reset();
        // Refresh the podcasts list
        loadPodcasts();
      } else {
        document.getElementById("formAlert").innerHTML = `<div class="alert alert-danger">${result.detail || "Error creating podcast"}</div>`;
      }
    } catch (error) {
      document.getElementById("formAlert").innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
  });