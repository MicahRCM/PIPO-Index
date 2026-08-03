$(function () {
    $("#nav-placeholder").load("toolbar.html");
});

const PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#1a8dc7", "#3541d4", "#e74c3c", "#27ae60", "#f39c12"
];

let retentionData = null;       // { years: [...], universities: { unitid: {name, rates} } }
let sortedUnis = [];            // [{unitid, name, rates, hasData}]
let selected = new Map();       // unitid -> color
let chart = null;

function buildChart(years) {
    const ctx = document.getElementById("retentionChart").getContext("2d");
    chart = new Chart(ctx, {
        type: "line",
        data: { labels: years, datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            spanGaps: true,
            tooltips: {
                mode: "nearest",
                intersect: false,
                callbacks: {
                    label: function (item, data) {
                        const ds = data.datasets[item.datasetIndex];
                        const v = item.yLabel;
                        return ds.label + ": " + (v == null ? "n/a" : v + "%");
                    }
                }
            },
            hover: { mode: "nearest", intersect: false },
            legend: { position: "bottom" },
            scales: {
                yAxes: [{
                    ticks: { suggestedMin: 40, suggestedMax: 100, callback: v => v + "%" },
                    scaleLabel: { display: true, labelString: "Retention rate" }
                }],
                xAxes: [{
                    scaleLabel: { display: true, labelString: "Fall cohort year" }
                }]
            }
        }
    });
}

function colorFor(unitid) {
    // Stable but cycling palette assignment based on insertion order.
    const idx = selected.size % PALETTE.length;
    return PALETTE[idx];
}

function refreshChart() {
    if (!chart) return;
    chart.data.datasets = Array.from(selected.entries()).map(([unitid, color]) => {
        const u = retentionData.universities[unitid];
        return {
            label: u.name,
            data: u.rates,
            borderColor: color,
            backgroundColor: color,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6,
            borderWidth: 2,
            lineTension: 0.15
        };
    });
    chart.update();
    updateCount();
}

function updateCount() {
    const n = selected.size;
    const el = document.getElementById("selectionCount");
    el.textContent = n === 0
        ? "Pick universities from the list to compare."
        : n + " selected (click a university to toggle).";
}

function renderList(filter) {
    const list = document.getElementById("uniList");
    const f = (filter || "").trim().toLowerCase();
    const selectedRows = [];
    const otherRows = [];
    // Preserve selection order so the legend / list order match.
    const selectionOrder = new Map();
    let idx = 0;
    for (const uid of selected.keys()) selectionOrder.set(uid, idx++);
    for (const u of sortedUnis) {
        if (f && !u.name.toLowerCase().includes(f)) continue;
        const isSel = selected.has(u.unitid);
        const swatchStyle = isSel
            ? "background:" + selected.get(u.unitid) + ";"
            : "";
        const html =
            '<div class="uniRow' + (isSel ? ' selected' : '') + '" data-unitid="' + u.unitid + '">' +
            '<span class="uniSwatch" style="' + swatchStyle + '"></span>' +
            '<span class="uniRowName">' + escapeHtml(u.name) +
            (u.hasData ? '' : '<span class="noDataNote">(no data)</span>') +
            '</span>' +
            '</div>';
        if (isSel) {
            selectedRows.push({ order: selectionOrder.get(u.unitid), html });
        } else {
            otherRows.push(html);
        }
    }
    selectedRows.sort((a, b) => a.order - b.order);
    const rows = selectedRows.map(r => r.html).concat(otherRows);
    if (selectedRows.length && otherRows.length) {
        rows.splice(selectedRows.length, 0, '<div class="listDivider"></div>');
    }
    list.innerHTML = rows.length
        ? rows.join("")
        : '<div class="loadingMsg">No matches</div>';
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
}

function toggleUni(unitid) {
    const u = retentionData.universities[unitid];
    if (!u) return;
    const hasData = Array.isArray(u.rates) && u.rates.some(v => v !== null);
    if (!hasData) return;
    if (selected.has(unitid)) {
        selected.delete(unitid);
    } else {
        selected.set(unitid, colorFor(unitid));
    }
    refreshChart();
    renderList(document.getElementById("uniSearch").value);
}

function loadData() {
    const d = window.RETENTION_DATA;
    if (!d || !d.universities) {
        document.getElementById("uniList").innerHTML =
            '<div class="loadingMsg">Failed to load data.</div>';
        return;
    }
    retentionData = d;
    sortedUnis = Object.entries(d.universities)
        .map(([unitid, info]) => ({
            unitid,
            name: info.name || "(Unnamed)",
            rates: info.rates,
            hasData: info.rates.some(v => v !== null)
        }))
        .sort((a, b) => {
            // unis with data first, then alphabetical
            if (a.hasData !== b.hasData) return a.hasData ? -1 : 1;
            return a.name.localeCompare(b.name);
        });
    buildChart(d.years);
    renderList("");
    updateCount();
}

document.addEventListener("DOMContentLoaded", function () {
    loadData();

    document.getElementById("uniSearch").addEventListener("input", function () {
        renderList(this.value);
    });

    document.getElementById("uniList").addEventListener("click", function (e) {
        const row = e.target.closest(".uniRow");
        if (!row) return;
        toggleUni(row.getAttribute("data-unitid"));
    });

    document.getElementById("clearBtn").addEventListener("click", function () {
        selected.clear();
        refreshChart();
        renderList(document.getElementById("uniSearch").value);
    });
});
