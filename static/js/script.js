function togglePassword(id) {
    const input = document.getElementById(id);
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
}

function confirmDelete(message) {
    return window.confirm(message || "Are you sure you want to delete this record?");
}

document.addEventListener("DOMContentLoaded", function () {
    const registerCards = document.querySelectorAll(".register-role:not(.disabled)");
    registerCards.forEach(function (card) {
        card.addEventListener("click", function () {
            registerCards.forEach(function (item) {
                item.classList.remove("selected");
            });
            card.classList.add("selected");

            const radio = card.querySelector("input[type='radio']");
            if (radio) radio.checked = true;
        });
    });

    const roleTabs = document.querySelectorAll(".role-tab");
    const roleInput = document.getElementById("loginRole");

    roleTabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            roleTabs.forEach(function (item) {
                item.classList.remove("selected");
            });
            tab.classList.add("selected");

            if (roleInput) {
                roleInput.value = tab.dataset.role || "";
            }
        });
    });

    document.querySelectorAll(".alert").forEach(function (alert) {
        setTimeout(function () {
            if (alert.classList.contains("show")) {
                alert.classList.remove("show");
            }
        }, 4500);
    });

    const forms = document.querySelectorAll("form");
    forms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const submitButton = form.querySelector("button[type='submit']:not(.btn-close)");
            if (submitButton && submitButton.classList.contains("form-button")) {
                submitButton.disabled = true;
                submitButton.innerText = "Please wait...";
            }
        });
    });
});
