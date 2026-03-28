document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Toggler ---
    const themeToggleButton = document.getElementById('theme-toggle');
    const sunIcon = document.getElementById('theme-toggle-sun');
    const moonIcon = document.getElementById('theme-toggle-moon');

    const applyTheme = (theme) => {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            sunIcon?.classList.remove('hidden');
            moonIcon?.classList.add('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            sunIcon?.classList.add('hidden');
            moonIcon?.classList.remove('hidden');
        }
    };

    // Set initial theme based on localStorage or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(savedTheme || (prefersDark ? 'dark' : 'light'));

    // Add click listener to the toggle button
    themeToggleButton?.addEventListener('click', () => {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });


    // --- FAQ Search (only on faq.html) ---
    const faqSearchInput = document.getElementById('faq-search');
    const faqItems = document.querySelectorAll('.faq-item');
    const faqCategories = document.querySelectorAll('.faq-category');

    faqSearchInput?.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();

        faqItems.forEach(item => {
            const question = item.querySelector('summary span:first-child').textContent.toLowerCase();
            const answer = item.querySelector('.faq-answer').textContent.toLowerCase();
            const isVisible = question.includes(searchTerm) || answer.includes(searchTerm);
            item.style.display = isVisible ? 'block' : 'none';
        });

        faqCategories.forEach(category => {
            const itemsInCategory = category.querySelectorAll('.faq-item');
            const allHidden = Array.from(itemsInCategory).every(item => item.style.display === 'none');
            category.style.display = allHidden ? 'none' : 'block';
        });
    });
});