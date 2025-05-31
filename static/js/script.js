// GitHub Repository Analyzer - Client-side JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Form validation for repository URL
    const repoForm = document.querySelector('form[action*="analyze"]');
    if (repoForm) {
        repoForm.addEventListener('submit', function(event) {
            const repoUrlInput = document.getElementById('repo_url');
            const repoUrl = repoUrlInput.value.trim();
            
            // Basic validation
            if (!repoUrl) {
                event.preventDefault();
                showAlert('Please enter a GitHub repository URL.', 'danger');
                return;
            }
            
            // Show loading state
            showLoading();
        });
    }
    
    // Example repository click handlers
    const exampleRepos = document.querySelectorAll('.example-repo');
    exampleRepos.forEach(function(repo) {
        repo.addEventListener('click', function() {
            const repoUrl = this.getAttribute('data-repo');
            document.getElementById('repo_url').value = repoUrl;
            
            // Scroll to form
            document.getElementById('repo_url').scrollIntoView({ behavior: 'smooth' });
            document.getElementById('repo_url').focus();
        });
    });
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize copy buttons for repository URLs
    initCopyButtons();
});

/**
 * Show a loading overlay
 */
function showLoading() {
    // Create loading overlay if it doesn't exist
    if (!document.getElementById('loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.zIndex = '9999';
        
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        
        const message = document.createElement('div');
        message.textContent = 'Analyzing repository...';
        message.style.color = 'white';
        message.style.marginLeft = '1rem';
        message.style.fontSize = '1.2rem';
        
        const content = document.createElement('div');
        content.style.display = 'flex';
        content.style.alignItems = 'center';
        content.appendChild(spinner);
        content.appendChild(message);
        
        overlay.appendChild(content);
        document.body.appendChild(overlay);
    } else {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
}

/**
 * Hide the loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Show an alert message
 * @param {string} message - The message to display
 * @param {string} type - The alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Create alert container if it doesn't exist
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }
    
    // Create alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add alert to container
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        alert.classList.remove('show');
        setTimeout(function() {
            alertContainer.removeChild(alert);
        }, 150);
    }, 5000);
}

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize copy buttons for repository URLs
 */
function initCopyButtons() {
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            
            // Create temporary textarea element
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            // Select and copy text
            textarea.select();
            document.execCommand('copy');
            
            // Remove temporary element
            document.body.removeChild(textarea);
            
            // Show success message
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-check"></i> Copied!';
            
            // Reset button text after 2 seconds
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 2000);
        });
    });
}
