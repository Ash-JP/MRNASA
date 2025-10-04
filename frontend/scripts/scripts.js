
function openModal() {
    document.getElementById('loginModal').style.display = 'flex';
}
function closeModal() {
    document.getElementById('loginModal').style.display = 'none';
}
function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    alert('Welcome, ' + username + '! Login functionality will connect to your backend.');
    closeModal();
}
window.onclick = function(event) {
    const modal = document.getElementById('loginModal');
    if (event.target === modal) {
        closeModal();
    }
}
