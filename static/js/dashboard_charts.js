document.addEventListener("DOMContentLoaded", function () {
    const salesDataEl = document.getElementById("sales-data");
    if (!salesDataEl) return;

    const salesChartCtx = document.getElementById("sales-over-time").getContext("2d");
    const salesData = JSON.parse(salesDataEl.textContent);

    new Chart(salesChartCtx, {
        type: "line",
        data: {
            labels: salesData.labels,
            datasets: [{
                label: "Sales (₦)",
                data: salesData.values,
                fill: false,
                borderColor: "rgb(75, 192, 192)",
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
});
