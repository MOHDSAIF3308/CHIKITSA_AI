// Smooth fade-in animation for cards on page load
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        setTimeout(() => {
            card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, i * 150);
    });

    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
});

// Prediction Form Handler
const predictForm = document.getElementById('predictForm');
if (predictForm) {
    predictForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const spinner = document.getElementById('spinner');
        const results = document.getElementById('results');
        const fileInput = e.target.querySelector('input[type="file"]');

        // Validate file
        if (!fileInput.files || !fileInput.files[0]) {
            showNotification('Please select an image file', 'warning');
            return;
        }

        // Show spinner with smooth transition
        results.classList.add('d-none');
        spinner.classList.remove('d-none');

        try {
            const res = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                throw new Error(`Server error: ${res.status}`);
            }

            const data = await res.json();

            // Update prediction with animation
            const predLabel = document.getElementById('predLabel');
            const predConf = document.getElementById('predConf');
            const confBar = document.getElementById('confBar');

            // Animate the label
            predLabel.style.opacity = '0';
            setTimeout(() => {
                predLabel.textContent = data.label;
                predLabel.style.transition = 'opacity 0.5s ease';
                predLabel.style.opacity = '1';
                
                // Set color based on prediction
                if (data.label.toLowerCase().includes('pneumonia')) {
                    predLabel.className = 'display-6 fw-bold text-danger mb-3';
                    confBar.classList.remove('bg-success');
                    confBar.classList.add('bg-danger');
                } else {
                    predLabel.className = 'display-6 fw-bold text-success mb-3';
                    confBar.classList.remove('bg-danger');
                    confBar.classList.add('bg-success');
                }
            }, 100);

            // Animate confidence
            predConf.textContent = `${data.confidence}% Confidence`;
            
            // Update intensity score if available
            if (data.intensity_score !== undefined) {
                const intensityScore = document.getElementById('intensityScore');
                if (intensityScore) {
                    intensityScore.textContent = `${data.intensity_score}%`;
                }
            }
            
            // Animate progress bar
            confBar.style.width = '0%';
            setTimeout(() => {
                confBar.style.width = `${data.confidence}%`;
            }, 200);

            // Show heatmap with fade-in
            if (data.overlay_url) {
                const img = document.getElementById('overlayImg');
                img.style.opacity = '0';
                img.src = data.overlay_url + '?t=' + Date.now();
                img.style.display = 'block';
                
                img.onload = () => {
                    img.style.transition = 'opacity 0.6s ease';
                    img.style.opacity = '1';
                };
            }

            // Show original image with fade-in
            if (data.original_url) {
                const originalImg = document.getElementById('originalImg');
                originalImg.style.opacity = '0';
                originalImg.src = data.original_url + '?t=' + Date.now();
                originalImg.style.display = 'block';
                
                originalImg.onload = () => {
                    originalImg.style.transition = 'opacity 0.6s ease';
                    originalImg.style.opacity = '1';
                };
            }

            // Show results with animation
            setTimeout(() => {
                spinner.classList.add('d-none');
                results.classList.remove('d-none');
            }, 500);

            // Show success notification
            showNotification('Analysis complete!', 'success');

        } catch (err) {
            console.error('Prediction error:', err);
            showNotification('Error analyzing image. Please try again.', 'danger');
            spinner.classList.add('d-none');
        }
    });

    // File input preview
    const fileInput = predictForm.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Show file name with animation
                const fileName = file.name;
                showNotification(`Selected: ${fileName}`, 'info');
            }
        });
    }
}

// Notification system
function showNotification(message, type = 'info') {
    const notificationContainer = document.createElement('div');
    notificationContainer.className = `alert alert-${type} alert-dismissible fade show`;
    notificationContainer.style.position = 'fixed';
    notificationContainer.style.top = '100px';
    notificationContainer.style.right = '20px';
    notificationContainer.style.zIndex = '9999';
    notificationContainer.style.minWidth = '300px';
    notificationContainer.style.animation = 'slideInRight 0.5s ease';
    
    notificationContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notificationContainer);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notificationContainer.style.animation = 'slideOutRight 0.5s ease';
        setTimeout(() => notificationContainer.remove(), 500);
    }, 5000);
}

// Auto-dismiss quote card after 10 seconds
const quoteCard = document.getElementById('quoteCard');
if (quoteCard) {
    setTimeout(() => {
        quoteCard.style.animation = 'slideOutRight 0.5s ease';
        setTimeout(() => quoteCard.remove(), 500);
    }, 10000);
}

// Add custom animations
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: rippleEffect 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes rippleEffect {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Parallax effect for background
document.addEventListener('mousemove', (e) => {
    const moveX = (e.clientX * 0.01);
    const moveY = (e.clientY * 0.01);
    
    const gradient = document.body;
    if (gradient) {
        gradient.style.backgroundPosition = `${moveX}px ${moveY}px`;
    }
});

// Download Report Function
function downloadReport() {
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv || resultsDiv.classList.contains('d-none')) {
        showNotification('No results to download', 'warning');
        return;
    }

    // Get all the data
    const label = document.getElementById('predLabel').textContent;
    const confidence = document.getElementById('predConf').textContent;
    const intensity = document.getElementById('intensityScore').textContent;
    const originalImg = document.getElementById('originalImg').src;
    const overlayImg = document.getElementById('overlayImg').src;

    // Create a printable report window
    const reportWindow = window.open('', '_blank');
    reportWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chiktisa A.I - Medical Report</title>
            <style>
                body {
                    font-family: 'Arial', sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: white;
                }
                .header {
                    text-align: center;
                    border-bottom: 3px solid #2563eb;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                .header h1 {
                    color: #2563eb;
                    margin: 0;
                }
                .header p {
                    color: #64748b;
                    margin: 5px 0;
                }
                .info-section {
                    background: #f8fafc;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }
                .info-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin-top: 15px;
                }
                .info-item {
                    text-align: center;
                }
                .info-label {
                    font-size: 12px;
                    color: #64748b;
                    text-transform: uppercase;
                }
                .info-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #1e293b;
                    margin-top: 5px;
                }
                .diagnosis-value {
                    color: ${label.includes('Pneumonia') ? '#ef4444' : '#10b981'};
                }
                .images-section {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .image-container {
                    text-align: center;
                }
                .image-container h3 {
                    color: #2563eb;
                    margin-bottom: 15px;
                }
                .image-container img {
                    max-width: 100%;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .footer {
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px solid #e2e8f0;
                    color: #64748b;
                    font-size: 12px;
                }
                .disclaimer {
                    background: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }
                @media print {
                    body { padding: 0; }
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 Chiktisa A.I</h1>
                <p>AI-Powered Pneumonia Detection Report</p>
                <p>Generated on: ${new Date().toLocaleString()}</p>
            </div>

            <div class="info-section">
                <h2 style="color: #1e293b; margin-top: 0;">Diagnosis Summary</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Diagnosis</div>
                        <div class="info-value diagnosis-value">${label}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Confidence</div>
                        <div class="info-value">${confidence}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Intensity Score</div>
                        <div class="info-value">${intensity}</div>
                    </div>
                </div>
            </div>

            <div class="disclaimer">
                <strong>⚠️ Important Notice:</strong> This report is generated by artificial intelligence and should be reviewed by a qualified medical professional. It is not a substitute for professional medical advice, diagnosis, or treatment.
            </div>

            <div class="images-section">
                <div class="image-container">
                    <h3>Original X-Ray Image</h3>
                    <img src="${originalImg}" alt="Original X-Ray">
                    <p style="color: #64748b; font-size: 14px; margin-top: 10px;">Uploaded chest X-ray for analysis</p>
                </div>
                <div class="image-container">
                    <h3>AI Attention Heatmap</h3>
                    <img src="${overlayImg}" alt="AI Heatmap">
                    <p style="color: #64748b; font-size: 14px; margin-top: 10px;">Colored regions indicate AI focus areas</p>
                </div>
            </div>

            <div class="footer">
                <p><strong>Chiktisa A.I</strong> - Advanced Medical Imaging Analysis</p>
                <p>This report is confidential and intended for medical professionals only.</p>
                <p>© 2025 Chiktisa A.I. All rights reserved.</p>
            </div>

            <div class="no-print" style="text-align: center; margin-top: 30px;">
                <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 12px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 5px;">
                    🖨️ Print Report
                </button>
                <button onclick="window.close()" style="background: #64748b; color: white; border: none; padding: 12px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 5px;">
                    ✕ Close
                </button>
            </div>
        </body>
        </html>
    `);
    reportWindow.document.close();
}

// Image Comparison Function
function showComparison(type) {
    const originalImg = document.getElementById('originalImg');
    const overlayImg = document.getElementById('overlayImg');
    
    if (!originalImg || !overlayImg) {
        showNotification('Images not loaded', 'warning');
        return;
    }

    const comparisonWindow = window.open('', '_blank', 'width=1200,height=800');
    const imgSrc = type === 'original' ? originalImg.src : overlayImg.src;
    const title = type === 'original' ? 'Original X-Ray Image' : 'AI Attention Heatmap';
    
    comparisonWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${title} - Chiktisa A.I</title>
            <style>
                body {
                    margin: 0;
                    padding: 20px;
                    background: #1e293b;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    font-family: Arial, sans-serif;
                }
                .header {
                    color: white;
                    text-align: center;
                    margin-bottom: 20px;
                }
                .image-viewer {
                    background: white;
                    padding: 20px;
                    border-radius: 15px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
                    max-width: 90%;
                }
                img {
                    max-width: 100%;
                    max-height: 70vh;
                    display: block;
                    border-radius: 10px;
                }
                .controls {
                    margin-top: 20px;
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                }
                button {
                    background: #2563eb;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: bold;
                }
                button:hover {
                    background: #1e40af;
                }
                .close-btn {
                    background: #ef4444;
                }
                .close-btn:hover {
                    background: #dc2626;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 ${title}</h1>
                <p>Chiktisa A.I - Medical Imaging Analysis</p>
            </div>
            <div class="image-viewer">
                <img src="${imgSrc}" alt="${title}">
            </div>
            <div class="controls">
                <button onclick="window.print()">🖨️ Print</button>
                <button class="close-btn" onclick="window.close()">✕ Close</button>
            </div>
        </body>
        </html>
    `);
    comparisonWindow.document.close();
}