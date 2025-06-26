/**
 * Frontend JavaScript for Multi-Repository Bitbucket LOC Analyzer
 * 
 * Handles form interactions, API communication, progress tracking,
 * and results display for the enhanced multi-repository analyzer.
 */

class BitbucketAnalyzerApp {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5001/api';
        this.currentJobId = null;
        this.progressInterval = null;
        
        this.initializeApp();
    }

    /**
     * Initialize the application
     */
    initializeApp() {
        this.bindEventListeners();
        this.setupFormValidation();
        this.setDefaultDates();
        this.setupRepositoryPreview();
    }

    /**
     * Bind all event listeners
     */
    bindEventListeners() {
        // Form submission
        const analysisForm = document.getElementById('analysis-form');
        analysisForm.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Test connection button
        const testConnectionBtn = document.getElementById('test-connection');
        testConnectionBtn.addEventListener('click', () => this.testConnection());

        // Repository slugs input for live preview
        const repoSlugsInput = document.getElementById('repo_slugs');
        repoSlugsInput.addEventListener('input', () => this.updateRepositoryPreview());

        // Progress section buttons
        const cancelBtn = document.getElementById('cancel-analysis');
        cancelBtn.addEventListener('click', () => this.cancelAnalysis());

        const newAnalysisBtn = document.getElementById('new-analysis');
        newAnalysisBtn.addEventListener('click', () => this.startNewAnalysis());

        // Results section buttons
        const startNewBtn = document.getElementById('start-new-analysis');
        startNewBtn.addEventListener('click', () => this.startNewAnalysis());

        const downloadAllBtn = document.getElementById('download-all');
        downloadAllBtn.addEventListener('click', () => this.downloadAllFiles());

        const viewReportBtn = document.getElementById('view-report');
        viewReportBtn.addEventListener('click', () => this.viewReport());

        // Modal close buttons
        const closeErrorModal = document.getElementById('close-error-modal');
        closeErrorModal.addEventListener('click', () => this.hideErrorModal());

        const errorOkBtn = document.getElementById('error-ok');
        errorOkBtn.addEventListener('click', () => this.hideErrorModal());

        // Form reset
        const form = document.getElementById('analysis-form');
        form.addEventListener('reset', () => {
            setTimeout(() => {
                this.setDefaultDates();
                this.hideRepositoryPreview();
                this.clearConnectionStatus();
            }, 50);
        });
    }

    /**
     * Set up form validation
     */
    setupFormValidation() {
        const requiredFields = ['token', 'base_url', 'workspace', 'repo_slugs', 'start_date', 'end_date'];
        
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('blur', () => this.validateField(field));
                field.addEventListener('input', () => this.clearFieldError(field));
            }
        });
    }

    /**
     * Set default dates (last 7 days)
     */
    setDefaultDates() {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 7);

        document.getElementById('end_date').value = endDate.toISOString().split('T')[0];
        document.getElementById('start_date').value = startDate.toISOString().split('T')[0];
    }

    /**
     * Setup repository preview functionality
     */
    setupRepositoryPreview() {
        this.updateRepositoryPreview();
    }

    /**
     * Update repository preview
     */
    updateRepositoryPreview() {
        const repoSlugsInput = document.getElementById('repo_slugs');
        const repoPreview = document.getElementById('repo-preview');
        const repoList = document.getElementById('repo-list');

        const value = repoSlugsInput.value.trim();
        
        if (!value) {
            this.hideRepositoryPreview();
            return;
        }

        // Parse repository slugs
        const repos = this.parseRepositoryInput(value);
        
        if (repos.length === 0) {
            this.hideRepositoryPreview();
            return;
        }

        // Show preview
        repoPreview.classList.remove('hidden');
        
        // Create repository list HTML
        const repoItems = repos.map((repo, index) => {
            const displayName = this.formatRepositoryName(repo);
            return `
                <div class="repo-item">
                    <span class="repo-number">${index + 1}.</span>
                    <span class="repo-slug">${repo}</span>
                    <span class="repo-display">→ "${displayName}"</span>
                </div>
            `;
        }).join('');

        repoList.innerHTML = `
            <div class="repo-count">Found ${repos.length} repositor${repos.length === 1 ? 'y' : 'ies'}:</div>
            ${repoItems}
        `;
    }

    /**
     * Hide repository preview
     */
    hideRepositoryPreview() {
        const repoPreview = document.getElementById('repo-preview');
        repoPreview.classList.add('hidden');
    }

    /**
     * Parse repository input string
     */
    parseRepositoryInput(input) {
        if (!input || !input.trim()) {
            return [];
        }

        // Split by newlines or commas and clean up
        const repos = input
            .split(/[\n,]+/)
            .map(repo => repo.trim())
            .filter(repo => repo.length > 0);

        return [...new Set(repos)]; // Remove duplicates
    }

    /**
     * Format repository name for display
     */
    formatRepositoryName(repoSlug) {
        return repoSlug
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Validate individual field
     */
    validateField(field) {
        const value = field.value.trim();
        
        if (field.hasAttribute('required') && !value) {
            this.showFieldError(field, 'This field is required');
            return false;
        }

        if (field.type === 'url' && value && !this.isValidUrl(value)) {
            this.showFieldError(field, 'Please enter a valid URL');
            return false;
        }

        if (field.type === 'date' && value) {
            const startDate = document.getElementById('start_date').value;
            const endDate = document.getElementById('end_date').value;
            
            if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
                this.showFieldError(field, 'Start date must be before end date');
                return false;
            }
        }

        this.clearFieldError(field);
        return true;
    }

    /**
     * Show field error
     */
    showFieldError(field, message) {
        this.clearFieldError(field);
        
        field.classList.add('error');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    /**
     * Clear field error
     */
    clearFieldError(field) {
        field.classList.remove('error');
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }

    /**
     * Validate URL
     */
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    /**
     * Test Bitbucket connection
     */
    async testConnection() {
        const token = document.getElementById('token').value.trim();
        const baseUrl = document.getElementById('base_url').value.trim();
        const workspace = document.getElementById('workspace').value.trim();

        if (!token || !baseUrl || !workspace) {
            this.showConnectionStatus('error', 'Please fill in token, base URL, and workspace fields');
            return;
        }

        const testBtn = document.getElementById('test-connection');
        const originalText = testBtn.textContent;
        
        try {
            testBtn.textContent = '🔄 Testing...';
            testBtn.disabled = true;
            
            this.showConnectionStatus('testing', 'Testing connection...');

            const response = await fetch(`${this.apiBaseUrl}/test-connection`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token,
                    base_url: baseUrl,
                    workspace
                })
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                this.showConnectionStatus('success', `✅ Connection successful to ${workspace}`);
            } else {
                this.showConnectionStatus('error', result.error || 'Connection failed');
            }

        } catch (error) {
            this.showConnectionStatus('error', `Connection failed: ${error.message}`);
        } finally {
            testBtn.textContent = originalText;
            testBtn.disabled = false;
        }
    }

    /**
     * Show connection status
     */
    showConnectionStatus(type, message) {
        const statusDiv = document.getElementById('connection-status');
        statusDiv.className = `connection-status ${type}`;
        statusDiv.textContent = message;
        statusDiv.style.display = 'block';
    }

    /**
     * Clear connection status
     */
    clearConnectionStatus() {
        const statusDiv = document.getElementById('connection-status');
        statusDiv.style.display = 'none';
        statusDiv.textContent = '';
        statusDiv.className = 'connection-status';
    }

    /**
     * Handle form submission
     */
    async handleFormSubmit(event) {
        event.preventDefault();

        // Validate form
        if (!this.validateForm()) {
            return;
        }

        // Collect form data
        const formData = this.collectFormData();
        
        try {
            this.showProgressSection();
            this.updateProgress(0, 'Initializing analysis...', 'Starting analysis job...');

            const response = await fetch(`${this.apiBaseUrl}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                this.currentJobId = result.job_id;
                this.startProgressTracking();
            } else {
                throw new Error(result.error || 'Failed to start analysis');
            }

        } catch (error) {
            this.showError(`Failed to start analysis: ${error.message}`);
            this.hideProgressSection();
        }
    }

    /**
     * Validate entire form
     */
    validateForm() {
        const requiredFields = ['token', 'base_url', 'workspace', 'repo_slugs', 'start_date', 'end_date'];
        let isValid = true;

        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Validate repository slugs
        const repoSlugs = document.getElementById('repo_slugs').value.trim();
        const repos = this.parseRepositoryInput(repoSlugs);
        
        if (repos.length === 0) {
            this.showFieldError(document.getElementById('repo_slugs'), 'Please enter at least one repository');
            isValid = false;
        }

        return isValid;
    }

    /**
     * Collect form data
     */
    collectFormData() {
        const repoSlugs = document.getElementById('repo_slugs').value.trim();
        const repos = this.parseRepositoryInput(repoSlugs);

        return {
            token: document.getElementById('token').value.trim(),
            base_url: document.getElementById('base_url').value.trim(),
            workspace: document.getElementById('workspace').value.trim(),
            repo_slugs: repos.join(', '), // Convert back to comma-separated for API
            start_date: document.getElementById('start_date').value,
            end_date: document.getElementById('end_date').value,
            group_by: document.getElementById('group_by').value,
            focus_user: document.getElementById('focus_user').value.trim() || null
        };
    }

    /**
     * Show progress section
     */
    showProgressSection() {
        document.getElementById('analysis-form-section').classList.add('hidden');
        document.getElementById('progress-section').classList.remove('hidden');
        document.getElementById('results-section').classList.add('hidden');
    }

    /**
     * Hide progress section
     */
    hideProgressSection() {
        document.getElementById('progress-section').classList.add('hidden');
        document.getElementById('analysis-form-section').classList.remove('hidden');
    }

    /**
     * Show results section
     */
    showResultsSection() {
        document.getElementById('progress-section').classList.add('hidden');
        document.getElementById('results-section').classList.remove('hidden');
    }

    /**
     * Start progress tracking
     */
    startProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            try {
                await this.checkJobStatus();
            } catch (error) {
                console.error('Error checking job status:', error);
                this.stopProgressTracking();
                this.showError(`Error tracking progress: ${error.message}`);
            }
        }, 2000); // Check every 2 seconds
    }

    /**
     * Stop progress tracking
     */
    stopProgressTracking() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    /**
     * Check job status
     */
    async checkJobStatus() {
        if (!this.currentJobId) return;

        const response = await fetch(`${this.apiBaseUrl}/jobs/${this.currentJobId}/status`);
        const status = await response.json();

        if (!response.ok) {
            throw new Error(status.error || 'Failed to get job status');
        }

        this.updateProgress(status.progress, status.status, status.message);

        if (status.status === 'completed') {
            this.stopProgressTracking();
            await this.loadResults();
        } else if (status.status === 'failed') {
            this.stopProgressTracking();
            this.showError(status.error || 'Analysis failed');
            this.hideProgressSection();
        }
    }

    /**
     * Update progress display
     */
    updateProgress(percentage, status, message) {
        document.getElementById('progress-percentage').textContent = `${Math.round(percentage)}%`;
        document.getElementById('progress-fill').style.width = `${percentage}%`;
        document.getElementById('progress-text').textContent = status;
        document.getElementById('progress-message').textContent = message;
    }

    /**
     * Cancel analysis
     */
    cancelAnalysis() {
        this.stopProgressTracking();
        this.currentJobId = null;
        this.hideProgressSection();
        this.showError('Analysis cancelled by user');
    }

    /**
     * Start new analysis
     */
    startNewAnalysis() {
        this.stopProgressTracking();
        this.currentJobId = null;
        
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('progress-section').classList.add('hidden');
        document.getElementById('analysis-form-section').classList.remove('hidden');
        
        // Clear previous results
        this.clearResults();
    }

    /**
     * Load and display results
     */
    async loadResults() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs/${this.currentJobId}/results`);
            const results = await response.json();

            if (!response.ok) {
                throw new Error(results.error || 'Failed to load results');
            }

            this.displayResults(results);
            this.showResultsSection();

        } catch (error) {
            this.showError(`Failed to load results: ${error.message}`);
            this.hideProgressSection();
        }
    }

    /**
     * Display analysis results
     */
    displayResults(results) {
        this.displayResultsSummary(results);
        this.displayRepositoryResults(results);
        this.displayCombinedResults(results);
        this.displayGeneratedFiles(results);
    }

    /**
     * Display results summary
     */
    displayResultsSummary(results) {
        const summaryDiv = document.getElementById('results-summary');
        const summary = results.summary || {};
        
        summaryDiv.innerHTML = `
            <div class="summary-grid">
                <div class="summary-card">
                    <h4>📁 Repositories Analyzed</h4>
                    <div class="summary-value">${summary.total_repositories || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>📊 Total Commits</h4>
                    <div class="summary-value">${summary.total_commits || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>➕ Lines Added</h4>
                    <div class="summary-value positive">${summary.total_additions || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>➖ Lines Deleted</h4>
                    <div class="summary-value negative">${summary.total_deletions || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>👥 Contributors</h4>
                    <div class="summary-value">${summary.total_contributors || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>📅 Date Range</h4>
                    <div class="summary-value">${summary.date_range || 'N/A'}</div>
                </div>
            </div>
        `;
    }

    /**
     * Display individual repository results
     */
    displayRepositoryResults(results) {
        const repoResultsDiv = document.getElementById('repository-results');
        const repositories = results.repositories || [];

        if (repositories.length === 0) {
            repoResultsDiv.innerHTML = '<p>No repository results available.</p>';
            return;
        }

        const repoCards = repositories.map(repo => `
            <div class="repo-result-card">
                <div class="repo-header">
                    <h4>📁 ${repo.display_name || repo.name}</h4>
                    <div class="repo-stats">
                        <span class="stat">📊 ${repo.commits || 0} commits</span>
                        <span class="stat positive">+${repo.additions || 0}</span>
                        <span class="stat negative">-${repo.deletions || 0}</span>
                    </div>
                </div>
                
                ${repo.chart_file ? `
                    <div class="repo-chart">
                        <img src="${this.apiBaseUrl.replace('/api', '')}/api/files/${repo.chart_file}/view" 
                             alt="Chart for ${repo.display_name || repo.name}" 
                             class="result-chart">
                    </div>
                ` : ''}
                
                <div class="repo-files">
                    ${repo.files ? repo.files.map(file => `
                        <a href="${this.apiBaseUrl}/files/${file}" 
                           class="file-link" target="_blank">
                            📄 ${file}
                        </a>
                    `).join('') : ''}
                </div>
            </div>
        `).join('');

        repoResultsDiv.innerHTML = `
            <h3>📁 Individual Repository Results</h3>
            <div class="repo-results-grid">
                ${repoCards}
            </div>
        `;
    }

    /**
     * Display combined results
     */
    displayCombinedResults(results) {
        const combinedDiv = document.getElementById('combined-results');
        const combined = results.combined || {};

        if (!combined.chart_file && !combined.files) {
            combinedDiv.innerHTML = '';
            return;
        }

        combinedDiv.innerHTML = `
            <h3>🔗 Combined Analysis</h3>
            <div class="combined-result-card">
                ${combined.chart_file ? `
                    <div class="combined-chart">
                        <img src="${this.apiBaseUrl.replace('/api', '')}/api/files/${combined.chart_file}/view" 
                             alt="Combined Analysis Chart" 
                             class="result-chart">
                    </div>
                ` : ''}
                
                <div class="combined-files">
                    ${combined.files ? combined.files.map(file => `
                        <a href="${this.apiBaseUrl}/files/${file}" 
                           class="file-link" target="_blank">
                            📄 ${file}
                        </a>
                    `).join('') : ''}
                </div>
            </div>
        `;
    }

    /**
     * Display generated files
     */
    displayGeneratedFiles(results) {
        const filesDiv = document.getElementById('files-list');
        const allFiles = results.all_files || [];

        if (allFiles.length === 0) {
            filesDiv.innerHTML = '<p>No files generated.</p>';
            return;
        }

        const fileGroups = this.groupFilesByType(allFiles);
        
        const fileGroupsHtml = Object.entries(fileGroups).map(([type, files]) => `
            <div class="file-group">
                <h4>${this.getFileTypeIcon(type)} ${type}</h4>
                <div class="file-list-group">
                    ${files.map(file => `
                        <div class="file-item">
                            <a href="${this.apiBaseUrl}/files/${file}" 
                               class="file-link" target="_blank">
                                📄 ${file}
                            </a>
                            <span class="file-size">${this.getFileSize(file)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        filesDiv.innerHTML = fileGroupsHtml;
    }

    /**
     * Group files by type
     */
    groupFilesByType(files) {
        const groups = {
            'Charts': [],
            'Data Files': [],
            'Reports': [],
            'Other': []
        };

        files.forEach(file => {
            const ext = file.split('.').pop().toLowerCase();
            if (['png', 'jpg', 'jpeg', 'svg'].includes(ext)) {
                groups['Charts'].push(file);
            } else if (['csv', 'json', 'xlsx'].includes(ext)) {
                groups['Data Files'].push(file);
            } else if (['md', 'txt', 'html', 'pdf'].includes(ext)) {
                groups['Reports'].push(file);
            } else {
                groups['Other'].push(file);
            }
        });

        // Remove empty groups
        Object.keys(groups).forEach(key => {
            if (groups[key].length === 0) {
                delete groups[key];
            }
        });

        return groups;
    }

    /**
     * Get file type icon
     */
    getFileTypeIcon(type) {
        const icons = {
            'Charts': '📊',
            'Data Files': '📋',
            'Reports': '📄',
            'Other': '📁'
        };
        return icons[type] || '📄';
    }

    /**
     * Get file size (placeholder - would need backend support)
     */
    getFileSize(filename) {
        // This would need to be provided by the backend
        return '';
    }

    /**
     * Download all files
     */
    async downloadAllFiles() {
        if (!this.currentJobId) {
            this.showError('No analysis results available for download');
            return;
        }

        try {
            const downloadBtn = document.getElementById('download-all');
            const originalText = downloadBtn.textContent;
            
            downloadBtn.textContent = '📦 Preparing Download...';
            downloadBtn.disabled = true;

            // In a real implementation, this would trigger a zip download
            // For now, we'll show a message
            this.showError('Download all functionality would be implemented here. For now, download files individually.');

        } catch (error) {
            this.showError(`Download failed: ${error.message}`);
        } finally {
            const downloadBtn = document.getElementById('download-all');
            downloadBtn.textContent = '📦 Download All Files';
            downloadBtn.disabled = false;
        }
    }

    /**
     * View report
     */
    viewReport() {
        if (!this.currentJobId) {
            this.showError('No analysis results available');
            return;
        }

        // Open results in a new window or modal
        window.open(`${this.apiBaseUrl.replace('/api', '')}/results/${this.currentJobId}`, '_blank');
    }

    /**
     * Clear all results
     */
    clearResults() {
        document.getElementById('results-summary').innerHTML = '';
        document.getElementById('repository-results').innerHTML = '';
        document.getElementById('combined-results').innerHTML = '';
        document.getElementById('files-list').innerHTML = '';
    }

    /**
     * Show error modal
     */
    showError(message) {
        document.getElementById('error-message').textContent = message;
        document.getElementById('error-modal').classList.remove('hidden');
    }

    /**
     * Hide error modal
     */
    hideErrorModal() {
        document.getElementById('error-modal').classList.add('hidden');
    }

    /**
     * Show loading overlay
     */
    showLoading(message = 'Processing...') {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bitbucketAnalyzer = new BitbucketAnalyzerApp();
});

// Additional utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
