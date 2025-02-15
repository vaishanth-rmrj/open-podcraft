// Function to load podcasts from the backend
async function loadPodcasts() {
  try {
    const response = await fetch("/api/podcasts/get");
    const podcasts = await response.json();
    const podcastList = document.getElementById("podcastList");
    podcastList.innerHTML = ''; // clear contents

    if (podcasts.length === 0) {
      podcastList.innerHTML = `
        <div class="px-2 mt-2 text-secondary">
          <h4>Create a new podcast to get started.</h4>
        </div>
      `;
    } else {
      podcasts.forEach(podcast => {
        const newContent = `
          <div class="container d-flex align-items-start border rounded p-3 m-3" style="width:600px;">
            <a href="/podcasts/${podcast.id}" class="text-decoration-none text-reset flex-grow-1">
              <div class="d-flex">
                <img src="/static/images/podcast_dp.webp" alt="${podcast.title}" class="rounded me-3" width="100px" height="100px">
                <div>
                  <h5 class="mb-1">${podcast.title}</h5>
                  <small>${podcast.description}</small>
                </div>
              </div>
            </a>
            <button class="btn btn-sm ms-3" onclick="deletePodcast('${podcast.id}')"><i class="fa-solid fa-trash text-danger"></i></button>
          </div>
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

async function deletePodcast(uuid) {
  if (!confirm("Are you sure you want to delete this podcast?")) {
    return;
  }
  try {
    const response = await fetch("/api/podcasts/delete", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ uuid }),
    });

    if (response.ok) {
      loadPodcasts();
    } else {
      const errorData = await response.json();
      console.error("Failed to delete podcast:", errorData.detail || errorData);
      alert("Failed to delete podcast.");
    }
  } catch (error) {
    console.error("Error deleting podcast:", error);
  }
}

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