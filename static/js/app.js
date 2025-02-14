// Function to load podcasts from the backend
async function loadPodcasts() {

  try {

    const response = await fetch("/api/podcasts/get");
    const podcasts = await response.json();
    const podcastList = document.getElementById("podcastList");
    podcastList.innerHTML = ''; // clear contents

    if (podcasts.length === 0) {
      podcastList.innerHTML = `
        <div class="alert alert-info">
          No podcasts are present.
        </div>
      `;

    } else {
      podcasts.forEach(podcast => {
        const newContent = `
            <a href="/podcasts/${podcast.id}" class="text-decoration-none text-reset">
                <div class="container d-flex border rounded p-3 m-3" style="width:400px;">
                    <img src="/static/images/audio_player_background.webp" alt="${podcast.title}" class="rounded me-3" width="100px" height="100px">
                    <div>
                      <h3 class="mb-1">${podcast.title}</h3>
                      <small>${podcast.description}</small>
                    </div>
                </div>
            </a>
        `;
        podcastList.insertAdjacentHTML("beforeend", newContent);
      });
    }

  } catch (error) {
    console.error("Error loading podcasts:", error);
  }
}
// Call loadPodcasts on page load
window.addEventListener("DOMContentLoaded", loadPodcasts);

// create podcast using modal
document.getElementById("podcastForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    // clear previous alerts
    document.getElementById("formAlert").innerHTML = "";

    // Gather form data
    const title = document.getElementById("title").value;
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
        
        document.getElementById("podcastForm").reset(); // reset the form        
        loadPodcasts(); // refresh the podcasts list

      } else {
        document.getElementById("formAlert").innerHTML = `
          <div class="alert alert-danger">
            ${result.detail || "Error creating podcast"}
          </div>
        `;

      }
    } catch (error) {
      document.getElementById("formAlert").innerHTML = `
        <div class="alert alert-danger">
          Error: ${error.message}
        </div>
      `;

    }
  });