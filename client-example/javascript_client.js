// Add JavaScript example for browser or Node.js
async function processFileQuestion(filePath, question, serverUrl = "http://localhost:8000") {
    const formData = new FormData();
    const fileInput = document.querySelector('input[type="file"]') || { files: [] };
    const file = fileInput.files[0];
    
    formData.append("question", question);
    formData.append("file", file);
    
    // Detect question type from file extension
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (fileExt === "md") {
        formData.append("question_type", "npx_readme");
    } else if (fileExt === "zip") {
        formData.append("question_type", "extract_zip");
    }
    
    try {
        const response = await fetch(`${serverUrl}/api/process`, {
            method: "POST",
            body: formData
        });
        return await response.json();
    } catch (error) {
        console.error("Error:", error);
        return { success: false, error: error.message };
    }
}