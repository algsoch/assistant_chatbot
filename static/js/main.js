
document.addEventListener('DOMContentLoaded', function() {
    // Fetch questions from vickys.json
    fetch('/static/vickys.json')
        .then(response => response.json())
        .then(data => {
            // Process and categorize questions
            const questions = processQuestionsData(data);
            
            // Initialize with GA1 questions
            displayPreloadedQuestions('GA1', questions);
            
            // Handle category switching
            const categoryTabs = document.querySelectorAll('.category-tab');
            categoryTabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    // Update active tab
                    categoryTabs.forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Display questions for the selected category
                    displayPreloadedQuestions(this.dataset.category, questions);
                });
            });
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            // Fall back to default questions
            displayDefaultQuestions();
        });

    const chatBox = document.getElementById('chatBox');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const preloadedQuestionsContainer = document.getElementById('preloadedQuestions');
    
    // Function to process questions from JSON
    function processQuestionsData(data) {
        const questions = [];
        
        data.forEach((item, index) => {
            if (item.file && item.question) {
                // Extract the category (GA1, GA2, etc.) from the file path
                const match = item.file.match(/GA(\d+)/i);
                const category = match ? `GA${match[1]}` : 'Other';
                
                // Create a shortened version of the question for display
                const shortText = item.question.split('.')[0];
                const displayText = shortText.length > 80 
                    ? shortText.substring(0, 80) + '...' 
                    : shortText;
                
                questions.push({
                    id: `question-${index}`,
                    category: category,
                    text: displayText,
                    fullText: item.question,
                    file: item.file
                });
            }
        });
        
        return questions;
    }
    
    // Display questions for a category
    function displayPreloadedQuestions(category, questions) {
        preloadedQuestionsContainer.innerHTML = '';
        
        const filteredQuestions = questions.filter(q => q.category === category);
        
        filteredQuestions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.textContent = question.text;
            questionItem.title = question.fullText;
            questionItem.dataset.file = question.file;
            questionItem.addEventListener('click', () => {
                // Set the full question or a simplified version
                questionInput.value = question.text;
                questionForm.dispatchEvent(new Event('submit'));
            });
            
            preloadedQuestionsContainer.appendChild(questionItem);
        });
        
        if (filteredQuestions.length === 0) {
            preloadedQuestionsContainer.innerHTML = '<div class="no-questions">No questions available for this category</div>';
        }
    }
    
    // Fall back to default questions if JSON loading fails
    function displayDefaultQuestions() {
        const defaultQuestions = [
            // GA1 Questions
            {"id": "ga1-1", "text": "What is the output of code -s?", "category": "GA1"},
            {"id": "ga1-2", "text": "Send a HTTPS request to httpbin.org with email parameter", "category": "GA1"},
            // More default questions can be added here
        ];
        
        const categoryTabs = document.querySelectorAll('.category-tab');
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                categoryTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Display default questions
                const category = this.dataset.category;
                const filtered = defaultQuestions.filter(q => q.category === category);
                
                preloadedQuestionsContainer.innerHTML = '';
                filtered.forEach(q => {
                    const div = document.createElement('div');
                    div.className = 'question-item';
                    div.textContent = q.text;
                    div.addEventListener('click', () => {
                        questionInput.value = q.text;
                        questionForm.dispatchEvent(new Event('submit'));
                    });
                    preloadedQuestionsContainer.appendChild(div);
                });
            });
        });
        
        // Initialize with GA1 questions
        categoryTabs[0].click();
    }

    // Handle sending messages
    window.sendQuestionWithFile = function(event) {
        event.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;
        
        // Display user question
        addMessage(question, 'user');
        
        // Clear input
        questionInput.value = '';
        
        // Display loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('Thinking...', 'bot loading', loadingId);
        
        // Create form data
        const formData = new FormData();
        formData.append('question', question);
        
        // Add file if present
        const fileInput = document.getElementById('fileAttachment');
        if (fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
        }
        
        fetch('/ask_with_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            // Display answer
            if (data.success) {
                addMessage(data.answer || "No response received", 'bot');
            } else {
                addMessage("Error: " + (data.error || "Unknown error occurred"), 'bot');
            }
        })
        .catch(error => {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) loadingMsg.remove();
            
            console.error('Error:', error);
            addMessage("Sorry, there was an error processing your question.", 'bot');
        });
    };
    
    // Function to add a message to the chat
    function addMessage(text, type, id = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        if (id) messageElement.id = id;
        
        // Process code blocks if it's a bot message
        if (type === 'bot' || type === 'bot loading') {
            // Code block detection for ```code``` blocks
            text = text.replace(/```([^`]+)```/g, function(match, codeContent) {
                return `<div class="code-block">${codeContent}<button class="copy-button">Copy</button></div>`;
            });
            
            // Inline code detection for `code`
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        }
        
        messageElement.innerHTML = text;
        
        // Add copy functionality to code blocks
        if (type === 'bot') {
            setTimeout(() => {
                messageElement.querySelectorAll('.copy-button').forEach(button => {
                    button.addEventListener('click', function() {
                        const codeBlock = this.parentNode;
                        const code = codeBlock.textContent.replace('Copy', '').trim();
                        
                        navigator.clipboard.writeText(code).then(() => {
                            this.textContent = 'Copied!';
                            setTimeout(() => { this.textContent = 'Copy'; }, 2000);
                        });
                    });
                });
            }, 0);
        }
        
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
        return messageElement;
    }
});
