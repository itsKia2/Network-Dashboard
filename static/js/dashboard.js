// Dashboard-specific JavaScript

// Auto-refresh functionality
let autoRefreshInterval;
let isAutoRefreshEnabled = true;

/**
 * Initialize dashboard functionality
 */
document.addEventListener("DOMContentLoaded", function () {
	initializeDashboard();
	setupAutoRefresh();
	setupEventListeners();
});

/**
 * Initialize dashboard
 */
function initializeDashboard() {
	console.log("Initializing dashboard...");
	loadDashboardData();
}

/**
 * Setup auto-refresh functionality
 */
function setupAutoRefresh() {
	const refreshInterval = 30000; // 30 seconds

	autoRefreshInterval = setInterval(() => {
		if (isAutoRefreshEnabled && document.visibilityState === "visible") {
			loadDashboardData();
		}
	}, refreshInterval);

	// Pause auto-refresh when page is not visible
	document.addEventListener("visibilitychange", function () {
		if (document.visibilityState === "hidden") {
			clearInterval(autoRefreshInterval);
		} else if (isAutoRefreshEnabled) {
			setupAutoRefresh();
			loadDashboardData();
		}
	});
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
	// Add click handlers for interactive elements
	document.addEventListener("click", function (e) {
		if (e.target.classList.contains("device-card")) {
			const deviceId = e.target.dataset.deviceId;
			if (deviceId) {
				showDeviceDetails(deviceId);
			}
		}
	});

	// Add keyboard shortcuts
	document.addEventListener("keydown", function (e) {
		// Ctrl/Cmd + R for manual refresh
		if ((e.ctrlKey || e.metaKey) && e.key === "r") {
			e.preventDefault();
			loadDashboardData();
			showNotification("Dashboard refreshed", "info");
		}

		// Space bar to toggle auto-refresh
		if (e.key === " " && e.target === document.body) {
			e.preventDefault();
			toggleAutoRefresh();
		}
	});
}

/**
 * Load all dashboard data
 */
async function loadDashboardData() {
	try {
		await Promise.all([
			loadStatistics(),
			loadRecentDevices(),
			loadNetworkStatus(),
		]);

		updateLastRefreshTime();
	} catch (error) {
		console.error("Error loading dashboard data:", error);
		showNotification("Error loading dashboard data", "error");
	}
}

/**
 * Load statistics data
 */
async function loadStatistics() {
	try {
		const response = await fetch("/api/stats");
		const data = await response.json();

		if (data.success) {
			updateStatisticsDisplay(data.stats);
		} else {
			console.error("Failed to load statistics:", data.error);
		}
	} catch (error) {
		console.error("Error loading statistics:", error);
	}
}

/**
 * Load recent devices data
 */
async function loadRecentDevices() {
	try {
		const response = await fetch("/api/devices/active?hours=24");
		const data = await response.json();

		if (data.success) {
			displayRecentDevices(data.devices.slice(0, 6));
			updateChartsData(data.devices);
		} else {
			console.error("Failed to load recent devices:", data.error);
		}
	} catch (error) {
		console.error("Error loading recent devices:", error);
	}
}

/**
 * Load network status
 */
async function loadNetworkStatus() {
	try {
		const response = await fetch("/api/scan/status");
		const data = await response.json();

		if (data.success) {
			updateScanStatus(data);
		} else {
			console.error("Failed to load network status:", data.error);
		}
	} catch (error) {
		console.error("Error loading network status:", error);
	}
}

/**
 * Update statistics display
 */
function updateStatisticsDisplay(stats) {
	const elements = {
		"total-devices": stats.total_devices,
		"active-devices": stats.active_devices,
		"new-today": stats.new_today,
	};

	Object.entries(elements).forEach(([id, value]) => {
		const element = document.getElementById(id);
		if (element) {
			animateNumber(element, parseInt(element.textContent) || 0, value);
		}
	});

	// Update last scan time
	const lastScanElement = document.getElementById("last-scan");
	if (lastScanElement && stats.last_scan) {
		const lastScan = new Date(stats.last_scan);
		lastScanElement.textContent = formatTimeAgo(lastScan);
	}
}

/**
 * Display recent devices
 */
function displayRecentDevices(devices) {
	const container = document.getElementById("recent-devices-grid");
	if (!container) return;

	container.innerHTML = "";

	if (devices.length === 0) {
		container.innerHTML =
			'<p class="no-devices-message">No active devices found</p>';
		return;
	}

	devices.forEach((device, index) => {
		const deviceCard = createDeviceCard(device, true);
		deviceCard.dataset.deviceId = device.id;
		deviceCard.style.animationDelay = `${index * 0.1}s`;
		deviceCard.classList.add("fade-in");
		container.appendChild(deviceCard);
	});
}

/**
 * Update charts with new data
 */
function updateChartsData(devices) {
	if (typeof deviceTypeChart !== "undefined") {
		updateDeviceTypeChart(devices);
	}

	if (typeof activityChart !== "undefined") {
		updateActivityChart(devices);
	}
}

/**
 * Update device type chart
 */
function updateDeviceTypeChart(devices) {
	const deviceTypes = {};

	devices.forEach((device) => {
		const type = device.device_type || "Unknown";
		deviceTypes[type] = (deviceTypes[type] || 0) + 1;
	});

	const labels = Object.keys(deviceTypes);
	const data = Object.values(deviceTypes);

	deviceTypeChart.data.labels = labels;
	deviceTypeChart.data.datasets[0].data = data;

	// Update colors based on device types
	deviceTypeChart.data.datasets[0].backgroundColor = labels.map((type) =>
		getDeviceTypeColor(type),
	);

	deviceTypeChart.update("none"); // Animate smoothly
}

/**
 * Update activity chart with mock time-series data
 */
function updateActivityChart(devices) {
	const now = new Date();
	const labels = [];
	const data = [];

	// Generate hourly data for the last 24 hours
	for (let i = 23; i >= 0; i--) {
		const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
		labels.push(hour.getHours().toString().padStart(2, "0") + ":00");

		// Simulate activity data based on current device count
		const baseActivity = Math.floor(devices.length * 0.7);
		const variation = Math.floor(
			Math.random() * Math.ceil(devices.length * 0.3),
		);
		data.push(Math.max(0, baseActivity + variation));
	}

	activityChart.data.labels = labels;
	activityChart.data.datasets[0].data = data;
	activityChart.update("none");
}

/**
 * Update scan status
 */
function updateScanStatus(statusData) {
	const scanButton = document.getElementById("scan-btn");
	if (!scanButton) return;

	if (statusData.scan_in_progress) {
		scanButton.disabled = true;
		scanButton.textContent = "Scanning...";
		scanButton.classList.add("scanning");
	} else {
		scanButton.disabled = false;
		scanButton.textContent = "Scan Network";
		scanButton.classList.remove("scanning");
	}
}

/**
 * Animate number changes
 */
function animateNumber(element, from, to, duration = 1000) {
	const startTime = Date.now();
	const difference = to - from;

	function updateNumber() {
		const elapsed = Date.now() - startTime;
		const progress = Math.min(elapsed / duration, 1);

		// Easing function for smooth animation
		const easeOutQuart = 1 - Math.pow(1 - progress, 4);
		const current = Math.round(from + difference * easeOutQuart);

		element.textContent = current;

		if (progress < 1) {
			requestAnimationFrame(updateNumber);
		}
	}

	requestAnimationFrame(updateNumber);
}

/**
 * Update last refresh time
 */
function updateLastRefreshTime() {
	const refreshIndicators = document.querySelectorAll(".last-refresh");
	const now = new Date();

	refreshIndicators.forEach((indicator) => {
		indicator.textContent = `Last updated: ${now.toLocaleTimeString()}`;
	});
}

/**
 * Toggle auto-refresh
 */
function toggleAutoRefresh() {
	isAutoRefreshEnabled = !isAutoRefreshEnabled;

	if (isAutoRefreshEnabled) {
		setupAutoRefresh();
		showNotification("Auto-refresh enabled", "success");
	} else {
		clearInterval(autoRefreshInterval);
		showNotification("Auto-refresh disabled", "info");
	}

	// Update UI indicator if it exists
	const indicator = document.getElementById("auto-refresh-indicator");
	if (indicator) {
		indicator.textContent = isAutoRefreshEnabled
			? "Auto-refresh: ON"
			: "Auto-refresh: OFF";
		indicator.className = isAutoRefreshEnabled
			? "indicator-on"
			: "indicator-off";
	}
}

/**
 * Show device details (if modal exists)
 */
function showDeviceDetails(deviceId) {
	// This would integrate with the device modal from devices.html
	console.log("Show details for device:", deviceId);

	// For now, navigate to devices page
	window.location.href = `/devices#device-${deviceId}`;
}

/**
 * Handle network topology visualization
 */
function initializeNetworkMap() {
	const mapContainer = document.querySelector(".network-nodes");
	if (!mapContainer) return;

	// Add hover effects to network nodes
	const nodes = mapContainer.querySelectorAll(".node");
	nodes.forEach((node) => {
		node.addEventListener("mouseenter", function () {
			this.style.transform = "scale(1.1)";
		});

		node.addEventListener("mouseleave", function () {
			this.style.transform = "scale(1)";
		});
	});
}

/**
 * Export dashboard data
 */
async function exportDashboardData() {
	try {
		const [devicesResponse, statsResponse] = await Promise.all([
			fetch("/api/devices"),
			fetch("/api/stats"),
		]);

		const devicesData = await devicesResponse.json();
		const statsData = await statsResponse.json();

		const exportData = {
			timestamp: new Date().toISOString(),
			statistics: statsData.success ? statsData.stats : null,
			devices: devicesData.success ? devicesData.devices : [],
			total_devices: devicesData.success ? devicesData.devices.length : 0,
		};

		exportAsJSON(
			exportData,
			`network_dashboard_${new Date().toISOString().split("T")[0]}.json`,
		);
		showNotification("Dashboard data exported successfully", "success");
	} catch (error) {
		console.error("Error exporting dashboard data:", error);
		showNotification("Failed to export dashboard data", "error");
	}
}

/**
 * Search devices from dashboard
 */
function searchDevices(query) {
	// This would integrate with a search interface
	console.log("Searching for:", query);
	window.location.href = `/devices?search=${encodeURIComponent(query)}`;
}

/**
 * Initialize dashboard tooltips
 */
function initializeTooltips() {
	const tooltipElements = document.querySelectorAll("[data-tooltip]");

	tooltipElements.forEach((element) => {
		element.addEventListener("mouseenter", function (e) {
			const tooltip = document.createElement("div");
			tooltip.className = "tooltip";
			tooltip.textContent = this.dataset.tooltip;

			document.body.appendChild(tooltip);

			const rect = this.getBoundingClientRect();
			tooltip.style.left =
				rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + "px";
			tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + "px";

			this.tooltipElement = tooltip;
		});

		element.addEventListener("mouseleave", function () {
			if (this.tooltipElement) {
				document.body.removeChild(this.tooltipElement);
				this.tooltipElement = null;
			}
		});
	});
}

/**
 * Performance monitoring
 */
function logPerformanceMetrics() {
	if (window.performance && window.performance.timing) {
		const timing = window.performance.timing;
		const loadTime = timing.loadEventEnd - timing.navigationStart;

		console.log(`Dashboard load time: ${loadTime}ms`);

		// Send to analytics if needed
		// analytics.track('dashboard_load_time', { duration: loadTime });
	}
}

// Initialize performance monitoring
window.addEventListener("load", logPerformanceMetrics);

// Initialize tooltips when DOM is ready
document.addEventListener("DOMContentLoaded", initializeTooltips);

// Initialize network map
document.addEventListener("DOMContentLoaded", initializeNetworkMap);

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
    .fade-in {
        animation: fadeIn 0.5s ease-in-out forwards;
        opacity: 0;
    }

    @keyframes fadeIn {
        to {
            opacity: 1;
        }
    }

    .scanning {
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.7);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(102, 126, 234, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(102, 126, 234, 0);
        }
    }

    .tooltip {
        position: absolute;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 1000;
        pointer-events: none;
        white-space: nowrap;
    }

    .tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: rgba(0, 0, 0, 0.8) transparent transparent transparent;
    }

    .no-devices-message {
        text-align: center;
        color: #666;
        font-style: italic;
        padding: 2rem;
        grid-column: 1 / -1;
    }
`;
document.head.appendChild(style);
