function openModal(type) {
  document.getElementById('authModal').classList.remove('hidden');
  document.getElementById('authModal').classList.add('flex');
  switchAuth(type);
}

function closeModal() {
  document.getElementById('authModal').classList.add('hidden');
  document.getElementById('authModal').classList.remove('flex');
}

function switchAuth(type) {
  document.getElementById('loginForm').classList.toggle('hidden', type !== 'login');
  document.getElementById('signupForm').classList.toggle('hidden', type !== 'signup');
}

function toggleTheme() {
  const isLight = document.documentElement.classList.toggle('light-mode');
  localStorage.setItem('copenny_theme', isLight ? 'light' : 'dark');
  updateThemeIcons();
}

function updateThemeIcons() {
  const isLight = document.documentElement.classList.contains('light-mode');
  const sunIcon = document.getElementById('sunIcon');
  const moonIcon = document.getElementById('moonIcon');
  if (sunIcon && moonIcon) {
    sunIcon.classList.toggle('hidden', isLight);
    moonIcon.classList.toggle('hidden', !isLight);
  }
}

async function handleLogin() {
  const loginForm = document.getElementById('loginForm');
  const isLogin = !loginForm.classList.contains('hidden');

  const emailId = isLogin ? 'loginEmail' : 'signupEmail';
  const passId = isLogin ? 'loginPass' : 'signupPass';
  const nameId = 'signupName';

  const email = document.getElementById(emailId).value.trim();
  const password = document.getElementById(passId).value.trim();
  const name = isLogin ? '' : document.getElementById(nameId).value.trim();

  if (!email || !email.includes('@')) {
    alert('Please enter a valid email address.');
    return;
  }
  if (!password) {
    alert('Please enter your password.');
    return;
  }
  if (!isLogin && !name) {
    alert('Please enter your name.');
    return;
  }

  const endpoint = isLogin ? '/auth/login' : '/auth/register';
  const payload = isLogin ? { email, password } : { email, password, name };

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.success) {
      localStorage.setItem('copenny_authenticated', 'true');
      localStorage.setItem('copenny_user_id', data.user_id);
      localStorage.setItem('copenny_user_name', data.name || name);
      localStorage.setItem('copenny_user_email', email);

      localStorage.setItem('copenny_user_email', email);

      if (isLogin) {
        window.location.href = '/ui';
      } else {
        // Show plan selection modal after signup
        closeModal();
        showPlanModal();
      }
    } else {
      alert(data.error || 'Authentication failed. Please check your credentials.');
    }
  } catch (err) {
    console.error('Auth error:', err);
    alert('Connectivity Error: ' + err.message + '\n\nPlease ensure the backend server is running on port 8080.');
  }
}

function showPlanModal() {
  const modal = document.getElementById('planModal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

async function selectPlan(tier) {
  const userId = localStorage.getItem('copenny_user_id');
  if (!userId) return;

  try {
    const response = await fetch('/subscription/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        tier: tier,
        months: 1
      })
    });

    const data = await response.json();
    if (data.success) {
      localStorage.setItem('copenny_user_tier', tier);
      window.location.href = '/ui';
    } else {
      alert('Error selecting plan: ' + (data.error || 'Unknown error'));
    }
  } catch (err) {
    console.error('Plan selection error:', err);
    alert('Failed to save plan selection.');
  }
}

function enterDashboard() {
  // Always attempt to go to the UI, the backend will redirect if not authorized
  window.location.href = '/ui';
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Theme init
  if (localStorage.getItem('copenny_theme') === 'light') {
    document.documentElement.classList.add('light-mode');
  }
  updateThemeIcons();

  const authModal = document.getElementById('authModal');
  if (authModal) {
    authModal.addEventListener('click', (e) => {
      if (e.target === authModal) closeModal();
    });
  }

  // Handle errors from backend redirects
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('error') === 'unauthorized') {
    openModal('login');
  }
});
