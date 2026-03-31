document.getElementById("exitForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const form = this;
    const submitBtn = document.querySelector(".submit-btn");

    // RESET OLD ERRORS
    document.querySelectorAll(".error-message").forEach(e => e.remove());
    document.querySelectorAll(".error-field").forEach(e => e.classList.remove("error-field"));

    let isValid = true;

    function showError(input, message) {
        setError(input, message);
        isValid = false;
    }

    function validateText(input, name) {
        const value = input.value.trim();
        const regex = /^[A-Za-z ]+$/;

        if (!value) {
            showError(input, `${name} is required`);
        } else if (!regex.test(value)) {
            showError(input, `${name} must contain alphabets only`);
        }
    }

    function validateContact(input) {
        const value = input.value.trim();
        const regex = /^[0-9]{10}$/;

        if (!regex.test(value)) {
            showError(input, "Contact must be exactly 10 digits");
        }
    }

    function validateDate(input) {
        const value = input.value;
        if (!value) return;

        const selected = new Date(value);
        const today = new Date();

        if (selected > today) {
            showError(input, "Date cannot be in future");
        }
    }

    // ================= FIELD VALIDATION =================

    validateText(document.getElementById("name"), "Name");
    validateText(document.getElementById("manager"), "Manager");
    validateText(document.getElementById("place"), "Place");

    validateContact(document.getElementById("contact"));
    validateDate(document.getElementById("date"));
    validateDate(document.getElementById("sign_date"));

    // ================= RANKING VALIDATION =================

    let ratingGroups = [
        "q1","q2","q3","q4","q5","q6","q7",
        "r1","r2","r3","r4",
        "kpca1","kpca2","kpca3","kpca4","kpca5","kpca6","kpca7","kpca8","kpca9",
        "mgr1","mgr2","mgr3","mgr4","mgr5","mgr6","mgr7","mgr8","mgr9","mgr10"
    ];

    let rankingError = false;

    ratingGroups.forEach(name => {
        if (!document.querySelector(`input[name="${name}"]:checked`)) {
            rankingError = true;
        }
    });

    if (rankingErrorBox) {
        if (rankingError) {
            rankingErrorBox.innerText = "Please select your recommendation for all questions";
            rankingErrorBox.style.display = "block";
            isValid = false;
        } else {
            rankingErrorBox.style.display = "none";
        }
    }

    // ================= SIGNATURE VALIDATION =================

    const signatureUpload = document.getElementById("signatureUpload");

    if (!signatureUpload.files.length) {
        setError(signatureUpload, "Signature is required");
        isValid = false;
    }

    // ================= STOP IF INVALID =================

    if (!isValid) return;

    // ================= SUBMIT =================

    submitBtn.disabled = true;
    submitBtn.innerText = "Submitting...";

    let formData = new FormData(form);

    try {
        let response = await fetch("/submit", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Server error");

        let result = await response.json();

        if (result.status === "success") {
            window.location.href = "/success?pdf=" + encodeURIComponent(result.pdf);
            return;
        } else {
            alert(result.message);
        }

    } catch (err) {
        alert("Submission failed");
    }

    submitBtn.disabled = false;
    submitBtn.innerText = "Submit";
});

// ================= LIVE VALIDATION =================

function setError(input, message) {
    input.classList.add("error-field");

    let error = input.parentNode.querySelector(".error-message");
    if (!error) {
        error = document.createElement("span");
        error.className = "error-message";
        input.parentNode.appendChild(error);
    }

    error.innerText = message;
}

function clearError(input) {
    input.classList.remove("error-field");

    let error = input.parentNode.querySelector(".error-message");
    if (error) error.remove();
}

// TEXT VALIDATION (Name, Manager, Place)
function liveTextValidation(input, fieldName) {
    input.addEventListener("input", function () {
        const value = this.value.trim();
        const regex = /^[A-Za-z ]*$/;

        if (!regex.test(value)) {
            setError(this, `${fieldName} must contain alphabets only`);
        } else if (value === "") {
            setError(this, `${fieldName} is required`);
        } else {
            clearError(this);
        }
    });
}

// CONTACT VALIDATION
function liveContactValidation(input) {
    input.addEventListener("input", function () {
        const value = this.value.trim();

        if (!/^\d*$/.test(value)) {
            setError(this, "Only numbers allowed");
        } else if (value.length > 10) {
            setError(this, "Maximum 10 digits allowed");
        } else if (/^\d{10}$/.test(value)) {
            clearError(this);
        } else {
            setError(this, "Contact must be 10 digits");
        }
    });
}

// DATE VALIDATION
function liveDateValidation(input) {
    input.addEventListener("input", function () {
        const value = this.value;
        if (!value) return;

        const selected = new Date(value);
        const today = new Date();

        if (selected > today) {
            setError(this, "Date cannot be in future");
        } else {
            clearError(this);
        }
    });
}

// ================= INITIALIZE =================

const nameEl = document.getElementById("name");
if (nameEl) liveTextValidation(nameEl, "Name");

const managerEl = document.getElementById("manager");
if (managerEl) liveTextValidation(managerEl, "Manager");

const placeEl = document.getElementById("place");
if (placeEl) liveTextValidation(placeEl, "Place");

const contactEl = document.getElementById("contact");
if (contactEl) liveContactValidation(contactEl, "Contact");


const dateEl = document.getElementById("date");
if (dateEl) liveDateValidation(dateEl, "Date");

const sign_dateEl = document.getElementById("sign_date");
if (sign_dateEl) liveDateValidation(sign_dateEl, "Sign_date");

let rankingErrorBox = document.getElementById("rankingError");

// ================= SIGNATURE PREVIEW =================

const signatureUpload = document.getElementById("signatureUpload");
const signaturePreview = document.getElementById("signaturePreview");
const removeSignatureBtn = document.getElementById("removeSignatureBtn");

if (signatureUpload && signaturePreview) {
    signatureUpload.addEventListener("change", function () {
        const file = this.files[0];

        if (file) {
            const url = URL.createObjectURL(file);
            signaturePreview.src = url;

            signaturePreview.onload = () => URL.revokeObjectURL(url);
        }
    });
}

if (removeSignatureBtn && signatureUpload && signaturePreview) {
    removeSignatureBtn.addEventListener("click", function () {
        signaturePreview.src = "";
        signatureUpload.value = "";
    });
}