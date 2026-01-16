/*
 * This file is part of NVDA add-ons stats.
 *
 * Copyright (C) 2026 Cyrille Bougot
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, see <https://www.gnu.org/licenses/>.
 */

"use strict";

let data = [];
let filteredData = [];
let currentSortKey = null;
let sortAscending = true;

// Filter state
let channelFilter = "all";   // all | stable | beta / dev
let statusFilter = "all";    // all | github_release | not_a_github_release

// Constants to represent GitHub statuses
const GITHUB_STATUS = {
  NOT_A_GITHUB_RELEASE: "NOT_A_GITHUB_RELEASE",
  ASSET_MISSING: "ASSET_MISSING",
  OK: "OK",
};

// Function returning the internal GitHub status code for an item
function getGithubStatusCode(item) {
  if (!item.on_github) {
    return GITHUB_STATUS.NOT_A_GITHUB_RELEASE;
  }
  if (item.asset_missing) {
    return GITHUB_STATUS.ASSET_MISSING;
  }
  // Could add more logic here for other statuses
  return GITHUB_STATUS.OK;
}

// User-facing status text, derived from internal status codes
function getStatus(item) {
  switch (getGithubStatusCode(item)) {
    case GITHUB_STATUS.NOT_A_GITHUB_RELEASE:
      return "Not a GitHub release";
    case GITHUB_STATUS.ASSET_MISSING:
      return "GitHub asset not found";
    // case GITHUB_STATUS.RATE_LIMITED:
    //   return "GitHub API rate limited";
    default:
      return "OK";
  }
}

// Define sorting order for GitHub statuses in submissionGroup (lowest first)
const GITHUB_STATUS_ORDER = {
  [GITHUB_STATUS.OK]: 0,
  [GITHUB_STATUS.ASSET_MISSING]: 1,
  [GITHUB_STATUS.NOT_A_GITHUB_RELEASE]: 2,
};

function submissionGroup(item) {
  // 0 = no date
  // 1 = has date
  return item.submission_time === null ? 0 : 1;
}

function updateSortIndicators() {
  document.querySelectorAll("th").forEach(th => {
    const button = th.querySelector("button");
    if (!button) return;

    const key = button.dataset.sort;
    if (key === currentSortKey) {
      th.setAttribute("aria-sort", sortAscending ? "ascending" : "descending");
      button.textContent = button.textContent.replace(/[▲▼]/g, "") + (sortAscending ? " ▲" : " ▼");
      button.setAttribute("aria-label", `${button.textContent.replace(/[▲▼]/g, "").trim()}, ${sortAscending ? "ascending" : "descending"}`);
    } else {
      th.setAttribute("aria-sort", "none");
      button.textContent = button.textContent.replace(/[▲▼]/g, "");
      button.setAttribute("aria-label", `${button.textContent.trim()}`);
    }
  });
}

function sortData(key, keepDirection = false) {
  if (!keepDirection) {
    if (currentSortKey === key) {
      sortAscending = !sortAscending;
    } else {
      currentSortKey = key;
      sortAscending = true;
    }
  } else {
    currentSortKey = key;
  }

  filteredData.sort((a, b) => {
    if (key === "submission_time") {
      // First criterion: group according to date (0 = no date, 1 = has date)
      const groupA = submissionGroup(a);
      const groupB = submissionGroup(b);

      if (groupA !== groupB) {
        return sortAscending ? groupA - groupB : groupB - groupA;
      }

      // If both have dates (group 1), sort by date
      if (groupA === 1) {
        const timeA = Number(a.submission_time);
        const timeB = Number(b.submission_time);
        if (timeA !== timeB) {
          return sortAscending ? timeA - timeB : timeB - timeA;
        }
      }

      // If same group and same date (or no date), sort by GitHub status
      const statusA = getGithubStatusCode(a);
      const statusB = getGithubStatusCode(b);
      if (statusA !== statusB) {
        return sortAscending
          ? GITHUB_STATUS_ORDER[statusB] - GITHUB_STATUS_ORDER[statusA]
          : GITHUB_STATUS_ORDER[statusA] - GITHUB_STATUS_ORDER[statusB];
      }

      // Otherwise stable (equality)
      return 0;
    }

    // Sorting for the status column
    if (key === "status") {
      const statusA = getGithubStatusCode(a);
      const statusB = getGithubStatusCode(b);

      if (statusA !== statusB) {
        return sortAscending
          ? GITHUB_STATUS_ORDER[statusA] - GITHUB_STATUS_ORDER[statusB]
          : GITHUB_STATUS_ORDER[statusB] - GITHUB_STATUS_ORDER[statusA];
      }
      return 0;
    }

    // Default sort for other columns
    let valA = a[key];
    let valB = b[key];

    if (valA === null) return 1;
    if (valB === null) return -1;

    if (typeof valA === "number" && typeof valB === "number") {
      return sortAscending ? valA - valB : valB - valA;
    }

    return sortAscending
      ? String(valA).localeCompare(String(valB))
      : String(valB).localeCompare(String(valA));
  });

  renderTable();
  updateSortIndicators();
}

function formatSubmissionTime(timestamp) {
  if (!timestamp) return "N/A";
  // timestamp is in ms
  return new Date(timestamp).toLocaleString();
}

function channelMatches(item) {
  if (channelFilter === "all") return true;
  return item.channel === channelFilter;
}

function statusMatches(item) {
  if (statusFilter === "all") return true;

  const status = getGithubStatusCode(item);

  if (statusFilter === "github_release") {
    // We accept OK and ASSET_MISSING because both are GitHub releases
    return status === GITHUB_STATUS.OK || status === GITHUB_STATUS.ASSET_MISSING;
  }

  if (statusFilter === "not_github_release") {
    return status === GITHUB_STATUS.NOT_A_GITHUB_RELEASE;
  }

  return true;
}

function applyFilters() {
  filteredData = data.filter(item =>
    channelMatches(item) &&
    statusMatches(item)
  );

  // Re-apply sorting on filtered data
  if (currentSortKey) {
    sortData(currentSortKey, true);
  } else {
    renderTable();
  }
}

function setChannelFilter(value) {
  channelFilter = value;
  applyFilters();
}

function setStatusFilter(value) {
  statusFilter = value;
  applyFilters();
}

function renderTable() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";

  filteredData.forEach(item => {
    const tr = document.createElement("tr");

    const nameTd = document.createElement("td");
    nameTd.textContent = item.name;

    const versionTd = document.createElement("td");
    versionTd.textContent = item.version;

    const channelTd = document.createElement("td");
    channelTd.textContent = item.channel;

    const publisherTd = document.createElement("td");
    publisherTd.textContent = item.publisher;

    const submissionTimeTd = document.createElement("td");
    submissionTimeTd.textContent = formatSubmissionTime(item.submission_time);

    const downloadsTd = document.createElement("td");
    downloadsTd.textContent =
      item.download_count !== null ? item.download_count : "N/A";

    const statusTd = document.createElement("td");
    statusTd.textContent = getStatus(item);

    tr.appendChild(nameTd);
    tr.appendChild(versionTd);
    tr.appendChild(channelTd);
    tr.appendChild(publisherTd);
    tr.appendChild(submissionTimeTd);
    tr.appendChild(downloadsTd);
    tr.appendChild(statusTd);

    tbody.appendChild(tr);
  });
}

function renderMeta(meta) {
  const p = document.getElementById("meta-info");

  const generated = meta.generated_at
    ? new Date(meta.generated_at).toLocaleString()
    : "Unknown";

  const duration = meta.generation_duration_seconds != null
    ? meta.generation_duration_seconds + " seconds"
    : "Unknown";

  p.textContent =
    `Data generated at: ${generated} - ` +
    `Generation time: ${duration}`;
}

document.querySelectorAll("th button").forEach(button => {
  button.addEventListener("click", () => {
    sortData(button.dataset.sort);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("channel-filter").addEventListener("change", (e) => {
    setChannelFilter(e.target.value);
  });

  document.getElementById("status-filter").addEventListener("change", (e) => {
    setStatusFilter(e.target.value);
  });

  fetch("https://raw.githubusercontent.com/CyrilleB79/NVDAAddonsStats/data/data.json")
    .then(response => response.json())
    .then(json => {
      data = json.items;
      document.getElementById("channel-filter").value = channelFilter;
      document.getElementById("status-filter").value = statusFilter;
      applyFilters();        // initialise filteredData
      sortData("name"); // already calls renderTable
      renderMeta(json.meta);
    })
    .catch(error => {
      console.error("Failed to load data.json:", error);
    });
});
