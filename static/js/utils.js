// Utility functions for the Network Dashboard

/**
 * Format a date to show how long ago it was
 * @param {Date} date - The date to format
 * @returns {string} - Formatted time ago string
 */
function formatTimeAgo(date) {
	const now = new Date();
	const diffInSeconds = Math.floor((now - date) / 1000);

	if (diffInSeconds < 60) {
		return "Just now";
	}

	const diffInMinutes = Math.floor(diffInSeconds / 60);
	if (diffInMinutes < 60) {
		return `${diffInMinutes} minute${diffInMinutes !== 1 ? "s" : ""} ago`;
	}

	const diffInHours = Math.floor(diffInMinutes / 60);
	if (diffInHours < 24) {
		return `${diffInHours} hour${diffInHours !== 1 ? "s" : ""} ago`;
	}

	const diffInDays = Math.floor(diffInHours / 24);
	if (diffInDays < 30) {
		return `${diffInDays} day${diffInDays !== 1 ? "s" : ""} ago`;
	}

	const diffInMonths = Math.floor(diffInDays / 30);
	if (diffInMonths < 12) {
		return `${diffInMonths} month${diffInMonths !== 1 ? "s" : ""} ago`;
	}

	const diffInYears = Math.floor(diffInMonths / 12);
	return `${diffInYears} year${diffInYears !== 1 ? "s" : ""} ago`;
}

/**
 * Create a device card element
 * @param {Object} device - Device data
 * @param {boolean} compact - Whether to show compact version
 * @returns {HTMLElement} - Device card element
 */
function createDeviceCard(device, compact = false) {
	const card = document.createElement("div");
	card.className = `device-card ${device.is_active ? "active" : "inactive"}`;

	const hostname = device.hostname || device.ip_address || "Unknown Device";
	const vendor = device.vendor || "Unknown Vendor";
	const deviceType = device.device_type || "Unknown";
	const lastSeen = device.last_seen
		? formatTimeAgo(new Date(device.last_seen))
		: "Unknown";
	const openPorts = Array.isArray(device.open_ports)
		? device.open_ports.length
		: 0;

	if (compact) {
		card.innerHTML = `
            <div class="device-header">
                <div>
                    <div class="device-name">${hostname}</div>
                    <div class="device-ip">${device.ip_address}</div>
                </div>
                <span class="status-badge ${device.is_active ? "status-active" : "status-inactive"}">
                    ${device.is_active ? "Active" : "Inactive"}
                </span>
            </div>
            <div class="device-details">
                <div class="device-detail">
                    <span class="device-detail-label">Type:</span>
                    <span class="device-detail-value">${deviceType}</span>
                </div>
                <div class="device-detail">
                    <span class="device-detail-label">Last Seen:</span>
                    <span class="device-detail-value">${lastSeen}</span>
                </div>
            </div>
        `;
	} else {
		card.innerHTML = `
            <div class="device-header">
                <div>
                    <div class="device-name">${hostname}</div>
                    <div class="device-ip">${device.ip_address}</div>
                </div>
                <span class="status-badge ${device.is_active ? "status-active" : "status-inactive"}">
                    ${device.is_active ? "Active" : "Inactive"}
                </span>
            </div>
            <div class="device-details">
                <div class="device-detail">
                    <span class="device-detail-label">MAC:</span>
                    <span class="device-detail-value">${device.mac_address || "Unknown"}</span>
                </div>
                <div class="device-detail">
                    <span class="device-detail-label">Vendor:</span>
                    <span class="device-detail-value">${vendor}</span>
                </div>
                <div class="device-detail">
                    <span class="device-detail-label">Type:</span>
                    <span class="device-detail-value">${deviceType}</span>
                </div>
                <div class="device-detail">
                    <span class="device-detail-label">Open Ports:</span>
                    <span class="device-detail-value">${openPorts}</span>
                </div>
                <div class="device-detail">
                    <span class="device-detail-label">Last Seen:</span>
                    <span class="device-detail-value">${lastSeen}</span>
                </div>
            </div>
        `;
	}

	return card;
}

/**
 * Get device type icon
 * @param {string} deviceType - Device type
 * @returns {string} - Icon emoji
 */
function getDeviceIcon(deviceType) {
	const iconMap = {
		Computer: "💻",
		"Mobile Device": "📱",
		"Router/Gateway": "🌐",
		"IoT Device": "🏠",
		Printer: "🖨️",
		Server: "🖥️",
		Unknown: "❓",
	};

	return iconMap[deviceType] || iconMap["Unknown"];
}

/**
 * Format MAC address consistently
 * @param {string} mac - MAC address
 * @returns {string} - Formatted MAC address
 */
function formatMacAddress(mac) {
	if (!mac) return "Unknown";

	// Remove any existing separators and convert to uppercase
	const cleanMac = mac.replace(/[:-]/g, "").toUpperCase();

	// Add colons every 2 characters
	return cleanMac.match(/.{2}/g).join(":");
}

/**
 * Validate IP address
 * @param {string} ip - IP address to validate
 * @returns {boolean} - Whether IP is valid
 */
function isValidIP(ip) {
	const ipRegex =
		/^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
	return ipRegex.test(ip);
}

/**
 * Validate MAC address
 * @param {string} mac - MAC address to validate
 * @returns {boolean} - Whether MAC is valid
 */
function isValidMAC(mac) {
	const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
	return macRegex.test(mac);
}

/**
 * Get color for device type
 * @param {string} deviceType - Device type
 * @returns {string} - CSS color
 */
function getDeviceTypeColor(deviceType) {
	const colorMap = {
		"Computer": "#007bff",
		"Mobile Device": "#28a745",
		"Router/Gateway": "#ffc107",
		"IoT Device": "#17a2b8",
		"Printer": "#6f42c1",
		"Server": "#fd7e14",
		"Unknown": "#6c757d",
	};

	return colorMap[deviceType] || colorMap["Unknown"];
}

/**
 * Sort devices by various criteria
 * @param {Array} devices - Array of devices
 * @param {string} sortBy - Sort criteria
 * @param {string} order - 'asc' or 'desc'
 * @returns {Array} - Sorted devices array
 */
function sortDevices(devices, sortBy, order = "asc") {
	const sortedDevices = [...devices].sort((a, b) => {
		let aVal, bVal;

		switch (sortBy) {
			case "hostname":
				aVal = (a.hostname || a.ip_address || "").toLowerCase();
				bVal = (b.hostname || b.ip_address || "").toLowerCase();
				break;
			case "ip":
				aVal = ipToNumber(a.ip_address);
				bVal = ipToNumber(b.ip_address);
				break;
			case "type":
				aVal = (a.device_type || "").toLowerCase();
				bVal = (b.device_type || "").toLowerCase();
				break;
			case "vendor":
				aVal = (a.vendor || "").toLowerCase();
				bVal = (b.vendor || "").toLowerCase();
				break;
			case "lastSeen":
				aVal = new Date(a.last_seen || 0);
				bVal = new Date(b.last_seen || 0);
				break;
			case "status":
				aVal = a.is_active ? 1 : 0;
				bVal = b.is_active ? 1 : 0;
				break;
			default:
				return 0;
		}

		if (aVal < bVal) return order === "asc" ? -1 : 1;
		if (aVal > bVal) return order === "asc" ? 1 : -1;
		return 0;
	});

	return sortedDevices;
}

/**
 * Convert IP address to number for sorting
 * @param {string} ip - IP address
 * @returns {number} - IP as number
 */
function ipToNumber(ip) {
	if (!ip) return 0;

	return ip.split(".").reduce((acc, octet, index) => {
		return acc + (parseInt(octet) << (8 * (3 - index)));
	}, 0);
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, delay) {
	let timeoutId;
	return function (...args) {
		clearTimeout(timeoutId);
		timeoutId = setTimeout(() => func.apply(this, args), delay);
	};
}

/**
 * Format bytes to human readable format
 * @param {number} bytes - Number of bytes
 * @returns {string} - Formatted string
 */
function formatBytes(bytes) {
	if (bytes === 0) return "0 Bytes";

	const k = 1024;
	const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));

	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * Get relative time string
 * @param {Date} date - Date to compare
 * @returns {string} - Relative time string
 */
function getRelativeTime(date) {
	const now = new Date();
	const diff = now - date;
	const seconds = Math.floor(diff / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);
	const days = Math.floor(hours / 24);

	if (seconds < 60) return "now";
	if (minutes < 60) return `${minutes}m`;
	if (hours < 24) return `${hours}h`;
	if (days < 7) return `${days}d`;

	return date.toLocaleDateString();
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise} - Copy operation promise
 */
async function copyToClipboard(text) {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch (err) {
		// Fallback for older browsers
		const textArea = document.createElement("textarea");
		textArea.value = text;
		textArea.style.position = "fixed";
		textArea.style.left = "-999999px";
		textArea.style.top = "-999999px";
		document.body.appendChild(textArea);
		textArea.focus();
		textArea.select();

		try {
			document.execCommand("copy");
			document.body.removeChild(textArea);
			return true;
		} catch (err) {
			document.body.removeChild(textArea);
			return false;
		}
	}
}

/**
 * Export data as JSON file
 * @param {Object} data - Data to export
 * @param {string} filename - Filename for export
 */
function exportAsJSON(data, filename = "network_devices.json") {
	const jsonStr = JSON.stringify(data, null, 2);
	const blob = new Blob([jsonStr], { type: "application/json" });
	const url = URL.createObjectURL(blob);

	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

/**
 * Export data as CSV file
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Filename for export
 */
function exportAsCSV(data, filename = "network_devices.csv") {
	if (!data.length) return;

	const headers = Object.keys(data[0]);
	const csvContent = [
		headers.join(","),
		...data.map((row) =>
			headers
				.map((header) => {
					const value = row[header];
					// Handle arrays and objects
					if (Array.isArray(value)) {
						return `"${value.join("; ")}"`;
					}
					if (typeof value === "object" && value !== null) {
						return `"${JSON.stringify(value)}"`;
					}
					// Escape quotes and wrap in quotes if contains comma
					const stringValue = String(value || "");
					if (
						stringValue.includes(",") ||
						stringValue.includes('"') ||
						stringValue.includes("\n")
					) {
						return `"${stringValue.replace(/"/g, '""')}"`;
					}
					return stringValue;
				})
				.join(","),
		),
	].join("\n");

	const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
	const url = URL.createObjectURL(blob);

	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}
