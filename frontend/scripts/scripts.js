// Loading screen functionality
window.addEventListener('load', function() {
    const worldImage = document.getElementById('worldImage');
    const loadingScreen = document.getElementById('loadingScreen');
    const scrollIndicator = document.getElementById('scrollIndicator');
    const mainContent = document.querySelectorAll('header, .container, footer');

    // Initially hide all main elements
    mainContent.forEach(el => el.classList.remove('visible'));
    
    // Function to show world background after loading
    function showWorldBackground() {
        loadingScreen.classList.add('fade-out');
        setTimeout(() => {
            loadingScreen.style.display = 'none';
            worldImage.classList.add('show'); // background appears
            if (scrollIndicator) {
                scrollIndicator.style.opacity = '1';
            }
        }, 600);
    }

    // Ensure world image is loaded
    if (worldImage.complete) {
        setTimeout(showWorldBackground, 2000);
    } else {
        worldImage.addEventListener('load', function() {
            setTimeout(showWorldBackground, 2000);
        });
    }
});

// Scroll detection to reveal content gradually
window.addEventListener('scroll', function() {
    const scrollPosition = window.scrollY;
    const header = document.querySelector('header');
    const container = document.querySelector('.container');
    const footer = document.querySelector('footer');
    const scrollIndicator = document.getElementById('scrollIndicator');
    const windowHeight = window.innerHeight;

    // Hide scroll indicator when scrolling starts
    if (scrollIndicator && scrollPosition > 10) {
        scrollIndicator.style.opacity = '0';
        scrollIndicator.style.pointerEvents = 'none';
    }

    // Reveal elements as user scrolls up or down
    [header, container, footer].forEach(el => {
        if (el) {
            const rect = el.getBoundingClientRect();
            if (rect.top < windowHeight * 0.9) {
                el.classList.add('visible');
            }
        }
    });
});

// Scroll indicator click scrolls slightly down
document.addEventListener('DOMContentLoaded', function() {
    const scrollIndicator = document.getElementById('scrollIndicator');
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', function() {
            window.scrollTo({
                top: window.innerHeight * 0.5,
                behavior: 'smooth'
            });
        });
    }
});

// Modal functions
function openModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.remove('active');
}

function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    console.log('Login attempt:', username);
    alert('Login functionality to be implemented');
    closeModal();
}

// Smooth scroll functions
function scrollToAbout() {
    const aboutSection = document.getElementById('about');
    if (aboutSection) {
        aboutSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function scrollToHelp() {
    const helpSection = document.getElementById('help');
    if (helpSection) {
        helpSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('loginModal');
    if (event.target === modal) {
        closeModal();
    }
}

window.addEventListener('scroll', function() {
    const worldImage = document.getElementById('worldImage');
    const scrollY = window.scrollY || document.documentElement.scrollTop;
    console.log(scrollY, window.innerHeight * 0.5);
    worldImage.style.opacity = (scrollY > window.innerHeight * 0.3) ? '1' : '0';
});

// Ensure content is visible if JavaScript loads after page
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.container');
    const footer = document.querySelector('footer');
    
    // Fallback: if loading screen is gone but content isn't visible, show it
    setTimeout(() => {
        const loadingScreen = document.getElementById('loadingScreen');
        if (loadingScreen && loadingScreen.style.display === 'none') {
            if (container && !container.classList.contains('visible')) {
                container.classList.add('visible');
            }
            if (footer && !footer.classList.contains('visible')) {
                footer.classList.add('visible');
            }
        }
    }, 100);

    
});