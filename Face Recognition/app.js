// SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
//
// SPDX-License-Identifier: MPL-2.0

const recentDetectionsElement = document.getElementById('recentClassifications');
const feedbackContentElement = document.getElementById('feedback-content');
const MAX_RECENT_SCANS = 5;
let scans = [];
const socket = io(`http://${window.location.host}`); // Initialize socket.io connection
let errorContainer = document.getElementById('error-container');

// Add a line here for every person you train.
// key = lowercase class label coming from the model (e.g. "kunj")
const PEOPLE = {
    kunj:    { name: "Kunj",    emoji: "👋", message: "Welcome back" },
    krishna: { name: "Krishna", emoji: "🙌", message: "Hey there" }
};

// Start the application
document.addEventListener('DOMContentLoaded', () => {
    initSocketIO();
    initializeConfidenceSlider();
    updatePersonFeedback(null);
    renderClasses();

    // Popover logic
    const confidencePopoverText = "Minimum confidence score for detected faces. Lower values show more results but may include false positives.";
    const feedbackPopoverText = "When the camera recognizes a known person, a greeting appears here.";

    document.querySelectorAll('.info-btn.confidence').forEach(img => {
        const popover = img.nextElementSibling;
        img.addEventListener('mouseenter', () => {
            popover.textContent = confidencePopoverText;
            popover.style.display = 'block';
        });
        img.addEventListener('mouseleave', () => {
            popover.style.display = 'none';
        });
    });

    document.querySelectorAll('.info-btn.feedback').forEach(img => {
        const popover = img.nextElementSibling;
        img.addEventListener('mouseenter', () => {
            popover.textContent = feedbackPopoverText;
            popover.style.display = 'block';
        });
        img.addEventListener('mouseleave', () => {
            popover.style.display = 'none';
        });
    });
});

function initSocketIO() {
    socket.on('connect', () => {
        if (errorContainer) {
            errorContainer.style.display = 'none';
            errorContainer.textContent = '';
        }
    });

    socket.on('disconnect', () => {
        if (errorContainer) {
            errorContainer.textContent = 'Connection to the board lost. Please check the connection.';
            errorContainer.style.display = 'block';
        }
    });

    socket.on('classifications', async (message) => {
        printClassifications(message);
        renderClasses();
    });

}

let lastChangeTimestamp = 0;
let currentState = 'none';
const UPDATE_INTERVAL = 2000; // 2 seconds

function printClassifications(newDetection) {
    scans.unshift(newDetection);
    if (scans.length > MAX_RECENT_SCANS) { scans.pop(); }

    // Parsing and handling the result for display
    try {
        const detections = JSON.parse(newDetection);

        // Pick the highest-confidence detection in this frame
        let top = null;
        if (Array.isArray(detections) && detections.length > 0) {
            top = detections.reduce((a, b) => (b.confidence > a.confidence ? b : a));
        }

        const newState = top ? top.content : 'none';
        const now = Date.now();

        if (newState !== currentState && (now - lastChangeTimestamp > UPDATE_INTERVAL)) {
            updatePersonFeedback(top);
            currentState = newState;
            lastChangeTimestamp = now;
        }
    } catch (e) {
        // In case of parsing error, show neutral state
        const now = Date.now();
        if ('none' !== currentState && (now - lastChangeTimestamp > UPDATE_INTERVAL)) {
            updatePersonFeedback(null);
            currentState = 'none';
            lastChangeTimestamp = now;
        }
    }
}

function updatePersonFeedback(detection) {
    const display = feedbackContentElement;
    display.innerHTML = ''; // Clear previous content

    // Nothing recognized -> neutral state
    if (!detection || !detection.content) {
        display.innerHTML = `
            <img src="img/stars.svg" alt="Waiting" style="width:80px;">
            <p class="feedback-text">No one recognized</p>
        `;
        return;
    }

    const key = detection.content.toLowerCase();
    const person = PEOPLE[key] || { name: detection.content, emoji: "🙂", message: "Recognized" };
    const pct = Math.floor(detection.confidence * 1000) / 10;

    display.innerHTML = `
        <div style="font-size:56px; line-height:1;">${person.emoji}</div>
        <div class="detection-text">${person.message}, <strong>${person.name}</strong>!</div>
        <div style="opacity:0.7; font-size:14px; margin-top:4px;">
            Recognized with ${pct}% confidence
        </div>
    `;
}

function renderClasses() {
    // Clear the list
    recentDetectionsElement.innerHTML = ``;

    if (scans.length === 0) {
        recentDetectionsElement.innerHTML = `
            <div class="no-recent-scans">
                <img src="./img/no-face.svg">
                No person detected yet
            </div>
        `;
        return;
    }

    scans.forEach((iscan) => {
        try {
            const iiscan = JSON.parse(iscan);

            if (iiscan.length === 0) {
                return; // Skip empty detection arrays
            }

            iiscan.forEach((scan) => {
                const row = document.createElement('div');
                row.className = 'scan-container';

                // Create a container for content and time
                const cellContainer = document.createElement('span');
                cellContainer.className = 'scan-cell-container cell-border';

                // Content (text + icon)
                const contentText = document.createElement('span');
                contentText.className = 'scan-content';
                const value = scan.confidence;
                const result = Math.floor(value * 1000) / 10;
                contentText.innerHTML = `${result}% - ${scan.content}`;

                // Time
                const timeText = document.createElement('span');
                timeText.className = 'scan-content-time';
                timeText.textContent = new Date(scan.timestamp).toLocaleString('it-IT').replace(',', ' -');

                // Append content and time to the container
                cellContainer.appendChild(contentText);
                cellContainer.appendChild(timeText);

                row.appendChild(cellContainer);
                recentDetectionsElement.appendChild(row);
            });
        } catch (e) {
            console.error("Failed to parse scan data:", iscan, e);
            // Display an error in the list itself
            if(recentDetectionsElement.getElementsByClassName('scan-error').length === 0) {
                const errorRow = document.createElement('div');
                errorRow.className = 'scan-error';
                errorRow.textContent = `Error processing detection data. Check console for details.`;
                recentDetectionsElement.appendChild(errorRow);
            }
        }
    });
}


function initializeConfidenceSlider() {
    const confidenceSlider = document.getElementById('confidenceSlider');
    const confidenceInput = document.getElementById('confidenceInput');
    const confidenceResetButton = document.getElementById('confidenceResetButton');

    confidenceSlider.addEventListener('input', updateConfidenceDisplay);
    confidenceInput.addEventListener('input', handleConfidenceInputChange);
    confidenceInput.addEventListener('blur', validateConfidenceInput);
    updateConfidenceDisplay();

    confidenceResetButton.addEventListener('click', (e) => {
        if (e.target.classList.contains('reset-icon') || e.target.closest('.reset-icon')) {
            resetConfidence();
        }
    });
}

function handleConfidenceInputChange() {
    const confidenceInput = document.getElementById('confidenceInput');
    const confidenceSlider = document.getElementById('confidenceSlider');

    let value = parseFloat(confidenceInput.value);

    if (isNaN(value)) value = 0.5;
    if (value < 0) value = 0;
    if (value > 1) value = 1;

    confidenceSlider.value = value;
    updateConfidenceDisplay();
}

function validateConfidenceInput() {
    const confidenceInput = document.getElementById('confidenceInput');
    let value = parseFloat(confidenceInput.value);

    if (isNaN(value)) value = 0.5;
    if (value < 0) value = 0;
    if (value > 1) value = 1;

    confidenceInput.value = value.toFixed(2);

    handleConfidenceInputChange();
}

function updateConfidenceDisplay() {
    const confidenceSlider = document.getElementById('confidenceSlider');
    const confidenceInput = document.getElementById('confidenceInput');
    const confidenceValueDisplay = document.getElementById('confidenceValueDisplay');
    const sliderProgress = document.getElementById('sliderProgress');

    const value = parseFloat(confidenceSlider.value);
    socket.emit('override_th', value); // Send confidence to backend
    const percentage = (value - confidenceSlider.min) / (confidenceSlider.max - confidenceSlider.min) * 100;

    const displayValue = value.toFixed(2);
    confidenceValueDisplay.textContent = displayValue;

    if (document.activeElement !== confidenceInput) {
        confidenceInput.value = displayValue;
    }

    sliderProgress.style.width = percentage + '%';
    confidenceValueDisplay.style.left = percentage + '%';
}

function resetConfidence() {
    const confidenceSlider = document.getElementById('confidenceSlider');
    const confidenceInput = document.getElementById('confidenceInput');

    confidenceSlider.value = '0.5';
    confidenceInput.value = '0.50';
    updateConfidenceDisplay();
}