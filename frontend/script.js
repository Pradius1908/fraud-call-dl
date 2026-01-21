document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('audio-file');
    const fileNameDisplay = document.getElementById('file-name');
    const analyzeBtn = document.getElementById('analyze-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const transcriptionContent = document.getElementById('transcription-content');
    const fraudBar = document.getElementById('fraud-bar');
    const scoreText = document.getElementById('score-text');

    // Handle file selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            fileNameDisplay.textContent = file.name;
            analyzeBtn.disabled = false;
            statusIndicator.innerText = "Ready to analyze";
        } else {
            fileNameDisplay.textContent = "No file chosen";
            analyzeBtn.disabled = true;
            statusIndicator.innerText = "Select an audio file to begin";
        }
    });

    analyzeBtn.addEventListener('click', uploadAndAnalyze);

    async function uploadAndAnalyze() {
        const file = fileInput.files[0];
        if (!file) {
            alert("No file selected!");
            return;
        }

        // UI Updates
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="icon">⏳</span> Analyzing...';
        statusIndicator.innerText = "Uploading & Processing...";
        transcriptionContent.innerHTML = '<p class="loading">Processing audio... this may take a moment depending on file size.</p>';
        fraudBar.style.width = '0%';
        scoreText.innerText = 'Analyzing...';

        // Reset colors
        fraudBar.style.background = `linear-gradient(90deg, #3b82f6, #8b5cf6)`;

        const formData = new FormData();
        formData.append('audio', file);

        try {
            const response = await fetch('http://localhost:5000/api/analyze', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }

            // Clear loading text
            transcriptionContent.innerHTML = '';

            // Show new text
            const newText = document.createElement('p');
            newText.innerText = result.text || "[No speech detected]";
            transcriptionContent.appendChild(newText);

            updateFraudBar(result.fraud_score, result.risk_level, result.detected_keywords);
            statusIndicator.innerText = "Analysis Complete";

        } catch (err) {
            console.error(err);
            statusIndicator.innerText = `Error: ${err.message}`;
            transcriptionContent.innerHTML = `<p class="error">Analysis failed: ${err.message}</p>`;
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span class="icon">🔍</span> Analyze File';
        }
    }

    function updateFraudBar(score, riskLevel, keywords) {
        // Score is 0 to 100
        const percentage = Math.max(score, 5); // Min 5% for visibility
        fraudBar.style.width = `${percentage}%`;

        // Update text
        scoreText.innerText = riskLevel;
        document.getElementById('score-number').innerText = score;

        // Color coding based on risk level
        let gradient = `linear-gradient(90deg, #10b981, #3b82f6)`; // Safe default

        if (score >= 80) { // Critical
            gradient = `linear-gradient(90deg, #dc2626, #7f1d1d)`;
        } else if (score >= 60) { // High
            gradient = `linear-gradient(90deg, #f59e0b, #ef4444)`;
        } else if (score >= 40) { // Medium
            gradient = `linear-gradient(90deg, #facc15, #f97316)`;
        } else if (score >= 20) { // Low
            gradient = `linear-gradient(90deg, #3b82f6, #6366f1)`;
        }

        fraudBar.style.background = gradient;

        // Render Keywords
        const riskFactorsContainer = document.getElementById('risk-factors');
        riskFactorsContainer.innerHTML = ''; // Clear previous

        if (keywords && keywords.length > 0) {
            const label = document.createElement('p');
            label.className = 'risk-label';
            label.innerText = 'Detected Risk Factors:';
            riskFactorsContainer.appendChild(label);

            const tagsDiv = document.createElement('div');
            tagsDiv.className = 'tags-container';

            keywords.forEach(k => {
                const tag = document.createElement('span');
                tag.className = `risk-tag risk-${k.level}`;
                tag.innerText = k.word;
                tagsDiv.appendChild(tag);
            });
            riskFactorsContainer.appendChild(tagsDiv);
        }
    }
});
