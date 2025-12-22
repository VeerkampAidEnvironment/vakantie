/* global L */

const map = L.map('map').setView([46.8, 9.8], 7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let vacations = [];
let layers = [];





const activityColors = {
  "wandelen": "#2E8B57",
  "via_ferrata": "#E74C3C",
  "fietsen": "#3498DB",
  "alpineren": "#1ABC9C"
};

function simplifyCoords(coords, tol = 0.0001) {
  if (!coords || coords.length < 3) return coords;
  const out = [coords[0]];
  let last = coords[0];
  for (let i = 1; i < coords.length; i++) {
    const p = coords[i];
    const dx = p[0] - last[0];
    const dy = p[1] - last[1];
    if (Math.sqrt(dx*dx + dy*dy) > tol) {
      out.push(p);
      last = p;
    }
  }
  const lastIn = coords[coords.length-1];
  if (out[out.length-1][0] !== lastIn[0] || out[out.length-1][1] !== lastIn[1]) {
    out.push(lastIn);
  }
  return out;
}

async function loadVacations() {
  const res = await fetch("/api/vacations");
  vacations = await res.json();
  buildSidebar();
  populateFilterOptions();
  addLegend();
  autoSelectFilters();
}

function buildSidebar() {
  const yearMap = new Map();
  vacations.forEach(v => {
    const y = String(v.year);
    if (!yearMap.has(y)) yearMap.set(y, []);
    yearMap.get(y).push(v);
  });

  const years = Array.from(yearMap.keys()).sort((a,b) => b-a);
  const container = document.getElementById('year-options');
  container.innerHTML = '';

  years.forEach(year => {
    const vacs = yearMap.get(year);
    const wrapper = document.createElement('div');
    wrapper.className = 'year-wrapper';

    const header = document.createElement('div');
    header.className = 'collapsible collapsed';
    header.innerHTML = `
      <label style="display:flex; align-items:center; gap:8px;">
        <input type="checkbox" class="year-check" value="${year}">
        <strong>${year}</strong>
      </label>
      <span class="arrow">▾</span>
    `;
    wrapper.appendChild(header);

    const vacList = document.createElement('div');
    vacList.className = 'vacation-list';
    vacList.style.display = 'none';

    vacs.forEach(v => {
      const lbl = document.createElement('label');
      lbl.className = 'year-item';
      lbl.innerHTML = `<input type="checkbox" class="vac-check" value="${v.folder}"> ${v.destination}`;
      vacList.appendChild(lbl);
    });

    wrapper.appendChild(vacList);
    container.appendChild(wrapper);

    header.addEventListener('click', e => {
      if (e.target.tagName === 'INPUT') return;
      const isCollapsed = header.classList.contains('collapsed');
      header.classList.toggle('collapsed', !isCollapsed);
      vacList.style.display = isCollapsed ? 'block' : 'none';
    });
  });

  attachYearCheckboxBehavior();
  attachVacCheckboxBehavior();
}

function attachYearCheckboxBehavior() {
  document.querySelectorAll('.year-wrapper').forEach(wrapper => {
    const header = wrapper.querySelector('.collapsible');
    const yearCheckbox = header.querySelector('.year-check');
    const vacCheckboxes = wrapper.querySelectorAll('.vac-check');

    yearCheckbox.addEventListener('change', () => {
      const anyUnchecked = Array.from(vacCheckboxes).some(cb => !cb.checked);
      vacCheckboxes.forEach(cb => cb.checked = anyUnchecked);
      yearCheckbox.checked = anyUnchecked;
      filterData();
    });
  });

  const selectAllBtn = document.getElementById('select-all-years');
  selectAllBtn.addEventListener('click', () => {
    const allYearCbs = document.querySelectorAll('.year-check');
    const allVacCbs = document.querySelectorAll('.vac-check');
    const anyUnchecked = Array.from(allYearCbs).some(cb => !cb.checked);
    allYearCbs.forEach(cb => cb.checked = anyUnchecked);
    allVacCbs.forEach(cb => cb.checked = anyUnchecked);
    filterData();
  });
}

function attachVacCheckboxBehavior() {
  document.querySelectorAll('.vac-check').forEach(cb => {
    cb.addEventListener('change', filterData);
  });
}

function populateFilterOptions() {
  const activityContainer = document.getElementById('activity-options');
  const participantContainer = document.getElementById('participant-options');

  const activitySet = new Set();
  const participantSet = new Set();

  vacations.forEach(v => {
    (v.activities || []).forEach(a => activitySet.add(a));
    (v.participants || []).forEach(p => participantSet.add(p));
  });

  activityContainer.innerHTML = '';
  participantContainer.innerHTML = '';

  Array.from(activitySet).sort().forEach(a => {
    const lbl = document.createElement('label');
    lbl.style.display = 'block';
    lbl.innerHTML = `<input type="checkbox" class="activity-check" value="${a}"> ${a}`;
    activityContainer.appendChild(lbl);
  });

  Array.from(participantSet).sort().forEach(p => {
    const lbl = document.createElement('label');
    lbl.style.display = 'block';
    lbl.innerHTML = `<input type="checkbox" class="participant-check" value="${p}"> ${p}`;
    participantContainer.appendChild(lbl);
  });

  document.querySelectorAll('.activity-check, .participant-check').forEach(cb => {
    cb.addEventListener('change', filterData);
  });
}

function autoSelectFilters() {
  document.querySelectorAll('#activity-options input[type=checkbox]').forEach(cb => cb.checked = true);
  document.querySelectorAll('#participant-options input[type=checkbox]').forEach(cb => cb.checked = true);
}

function filterData() {
  const selectedVacs = [...document.querySelectorAll('.vac-check:checked')].map(cb => cb.value);
  const selectedActs = [...document.querySelectorAll('.activity-check:checked')].map(cb => cb.value);
  const selectedParts = [...document.querySelectorAll('.participant-check:checked')].map(cb => cb.value);

  let finalFiltered = vacations.filter(v => selectedVacs.includes(v.folder));

  if (selectedActs.length) {
    finalFiltered = finalFiltered.filter(v => (v.activities || []).some(a => selectedActs.includes(a)));
  }
  if (selectedParts.length) {
    finalFiltered = finalFiltered.filter(v => (v.participants || []).some(p => selectedParts.includes(p)));
  }

  renderVacations(finalFiltered);
}

function renderVacations(data) {
  // Remove previous layers
  layers.forEach(l => map.removeLayer(l));
  layers = [];

  const fetchPromises = [];

  data.forEach(v => {

       // === ROUTES (GeoJSON – fast) =====================================
(v.geojson_files || []).forEach(geo => {
  const color = activityColors[geo.activity] || '#555';

  const activitySlug = geo.activity
    .toLowerCase()
    .replace(/\s+/g, "_");

  const url = `/vacation/${v.folder}/geojson/${activitySlug}/${geo.filename}`;



      const p = fetch(url)
        .then(r => {
          if (!r.ok) throw new Error("GeoJSON not found");
          return r.json();
        })
        .then(geojson => {
          const layer = L.geoJSON(geojson, {
            style: { color, weight: 3 },
            noClip: true
          }).addTo(map);

          layer.bindPopup(`
            <b>${v.destination} (${v.year})</b><br>
            Activiteit: ${geo.activity}<br>
            <a href="/vacation/${v.folder}">Details</a>
          `);

          layers.push(layer);
          return layer;
        })
        .catch(err => {
          console.warn("Failed loading GeoJSON:", url, err);
          return null;
        });

      fetchPromises.push(p);
    });



    //
    // === CLIMBING AREAS ==============================================
    //
    if (v.climbing) {
      for (const [areaName, area] of Object.entries(v.climbing)) {
        if (!area.coords || area.coords.length !== 2) continue;

        const marker = L.circleMarker(area.coords, {
          radius: 7,
          color: "#8e44ad",
          fillColor: "#8e44ad",
          fillOpacity: 0.85,
          weight: 2
        }).addTo(map);

        marker.bindPopup(`
          <b>${areaName}</b><br>
          Routes: ${area.routes ? area.routes.length : 0}<br>
          <a href="/vacation/${v.folder}">Details</a>
        `);

        layers.push(marker);
      }
    }

  }); // end forEach(vacation)



  //
  // === FIT MAP BOUNDS ================================================
  //
  Promise.all(fetchPromises).then(() => {
    const validLayers = layers.filter(Boolean);

    if (!validLayers.length) return;

    const group = L.featureGroup(validLayers);
    const bounds = group.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, { maxZoom: 14, padding: [40, 40] });
    }
  });
}

function addLegend() {
  const legend = L.control({position:'bottomright'});
  legend.onAdd = function() {
    const div = L.DomUtil.create('div','legend');
    div.innerHTML = '<h5>Activities</h5>';
    for (const [k,c] of Object.entries(activityColors)) {
      div.innerHTML += `<div style="display:flex; gap:8px; align-items:center; margin:4px 0">
        <span style="width:14px;height:14px;background:${c};display:inline-block;border-radius:3px;border:1px solid #666"></span>
        <span style="font-size:13px">${k}</span>
      </div>`;
    }
    return div;
  };
  legend.addTo(map);
}

loadVacations();