// Devices page JavaScript for real-time updates

document.addEventListener("DOMContentLoaded", function () {
	initializeDevicesPage();
});

function initializeDevicesPage() {
	loadDevicesData();
	setupSocketListeners();
}

// Allow external refresh (e.g. from scan notification)
window.refreshData = loadDevicesData;

async function loadDevicesData() {
	const spinner = document.getElementById("loading-spinner");
	const noDevices = document.getElementById("no-devices");
	const tbody = document.getElementById("devices-table-body");
	if (spinner) spinner.style.display = "block";
	if (noDevices) noDevices.style.display = "none";
	try {
		const [devicesRes, statsRes] = await Promise.all([
			fetch("/api/devices"),
			fetch("/api/stats")
		]);
		const devicesData = await devicesRes.json();
		const statsData = await statsRes.json();

		console.log("/api/devices response:", devicesData);
		console.log("/api/stats response:", statsData);

		if (devicesData.success) {
			updateDevicesTable(devicesData.devices);
			updateDeviceSummary(statsData.stats);
			if (devicesData.devices.length === 0 && noDevices) {
				noDevices.style.display = "block";
			}
		} else {
			if (tbody) tbody.innerHTML = "<tr><td colspan='11'>Error loading devices: " + (devicesData.error || "Unknown error") + "</td></tr>";
			if (noDevices) noDevices.style.display = "block";
		}
	} catch (error) {
		console.error("Error loading devices data:", error);
		if (tbody) tbody.innerHTML = "<tr><td colspan='11'>Error loading devices: " + error + "</td></tr>";
		if (noDevices) noDevices.style.display = "block";
	} finally {
		if (spinner) spinner.style.display = "none";
	}
}

function updateDevicesTable(devices) {
	const tbody = document.getElementById("devices-table-body");
	if (!tbody) return;
	tbody.innerHTML = "";
	devices.forEach(device => {
		const row = document.createElement("tr");
		// <td>${device.first_seen ? new Date(device.first_seen).toLocaleString() : "-"}</td>
		// IGNORE: First seen date is not needed in the current view
	row.innerHTML = `
		<td>${device.is_active ? '<span class="active-dot"></span> Active' : '<span class="inactive-dot"></span> Inactive'}</td>
		<td>${device.hostname || device.ip_address || "Unknown"}</td>
		<td>${device.ip_address || "-"}</td>
		<td>${device.mac_address || "-"}</td>
		<td>${device.vendor || "-"}</td>
		<td>${device.device_type || "-"}</td>
		<td>${Array.isArray(device.open_ports) ? device.open_ports.length : 0}</td>
		<td>${device.last_seen ? new Date(device.last_seen).toLocaleString() : "-"}</td>
		<td><!-- Actions --></td>
	`;
		tbody.appendChild(row);
	});
}

function updateDeviceSummary(stats) {
	document.getElementById("total-count").textContent = stats.total_devices;
	document.getElementById("active-count").textContent = stats.active_devices;
	// Add more summary updates as needed
}

function setupSocketListeners() {
	if (typeof io === "undefined") return;
	const socket = io();
	socket.on("device_update", data => {
		if (data.devices) updateDevicesTable(data.devices);
		if (data.stats) updateDeviceSummary(data.stats);
	});
}
