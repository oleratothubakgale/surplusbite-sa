const grid = document.getElementById('catalogue-grid');

function showSkeletons() {
    let skeletons = '';
    for(let i=0; i<6; i++) {
        skeletons += `<div class="skeleton-card"><div class="skeleton-shimmer"></div></div>`;
    }
    grid.innerHTML = skeletons;
}

// Mock Data with AI Categories
const mockData = [
    { id: "Heirloom Tomatoes", seller: "Green Valley Farm", card_url: "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=600&h=450&fit=crop", reduction_pct: "99.2%", ai_category: "produce", ai_status: "success" },
    { id: "Artisan Sourdough", seller: "City Bakery", card_url: "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&h=450&fit=crop", reduction_pct: "98.5%", ai_category: "bakery", ai_status: "success" },
    { id: "Margherita Pizza", seller: "Pizza Palace", card_url: "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&h=450&fit=crop", reduction_pct: "97.1%", ai_category: "prepared", ai_status: "success" },
    { id: "Cheddar Block", seller: "Dairy Delights", card_url: "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=600&h=450&fit=crop", reduction_pct: "96.8%", ai_category: "dairy", ai_status: "success" },
    // A test entry showing what happens if AI detects no food!
    { id: "My Selfie", seller: "Unknown", card_url: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&h=450&fit=crop", reduction_pct: "95.0%", ai_category: "unknown", ai_status: "no_food_detected" }
];

function getCategoryBadge(category, status) {
    if (status === "no_food_detected") {
        return `<span class="badge-category badge-warning">⚠️ Not Food</span>`;
    }
    const colors = {
        produce: "badge-green",
        bakery: "badge-orange",
        prepared: "badge-red",
        dairy: "badge-blue"
    };
    const colorClass = colors[category] || "badge-gray";
    return `<span class="badge-category ${colorClass}">${category.toUpperCase()}</span>`;
}

function renderCatalogue(data) {
    if (!data || data.length === 0) {
        grid.innerHTML = `<div class="empty-state">
            <h2>No listings yet</h2>
            <p>Upload a photo to see it appear here.</p>
        </div>`;
        return;
    }

    grid.innerHTML = data.map((item, index) => `
        <div class="card" style="animation-delay: ${index * 0.1}s">
            <div class="card-image-wrapper">
                <img src="${item.card_url}" alt="${item.id}" class="card-image" loading="lazy">
                <div class="category-badge-container">
                    ${getCategoryBadge(item.ai_category, item.ai_status)}
                </div>
            </div>
            <div class="card-content">
                <div class="card-title">${item.id}</div>
                <div class="card-seller">📍 ${item.seller}</div>
                <div class="card-stats">
                    <span class="badge-impact">⚡ ${item.reduction_pct} smaller</span>
                    <button class="btn-reserve">Reserve</button>
                </div>
            </div>
        </div>
    `).join('');

    attach3DTilt();
}

function attach3DTilt() {
    if (!window.matchMedia("(pointer: fine)").matches) return;

    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -10;
            const rotateY = ((x - centerX) / centerX) * 10;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)`;
            card.style.transition = "transform 0.5s ease";
        });
        
        card.addEventListener('mouseenter', () => {
            card.style.transition = "transform 0.1s ease-out";
        });
    });
}

showSkeletons();
setTimeout(() => {
    renderCatalogue(mockData);
}, 1500);