/**
 * Скрипт для создания скриншотов UI загрузок
 * Запуск: node e2e/scripts/take-screenshots.js
 */

const { chromium } = require('playwright');

(async () => {
  console.log('🚀 Запуск браузера...');
  
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  
  const page = await context.newPage();
  
  // Переходим на страницу загрузок
  console.log('📸 Переход на страницу загрузок...');
  await page.goto('http://localhost:8888/#uploads', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // Закрываем sidebar если открыт
  const sidebar = page.locator('#sidebar');
  const isSidebarOpen = await sidebar.isVisible();
  if (isSidebarOpen) {
    console.log('🚪 Закрытие sidebar...');
    await page.locator('#sidebar-toggle').click();
    await page.waitForTimeout(500);
  }
  
  // Скриншот всей страницы
  console.log('📷 Скриншот всей страницы...');
  await page.screenshot({ path: 'e2e/results/uploads_page_full.png', fullPage: true });
  
  // Находим все карточки
  const allCards = page.locator('.upload-card');
  const cardCount = await allCards.count();
  console.log(`📦 Найдено карточек: ${cardCount}`);
  
  for (let i = 0; i < cardCount; i++) {
    const card = allCards.nth(i);
    const title = await card.locator('h3').textContent();
    console.log(`  - ${title}`);
    
    // Скриншот карточки с force: true
    const safeTitle = title.replace(/[^a-zA-Zа-яА-Я0-9]/g, '_');
    try {
      await card.screenshot({ path: `e2e/results/upload_card_${i}_${safeTitle}.png`, force: true });
      console.log(`    ✓ Скриншот сохранён`);
    } catch (e) {
      console.log(`    ⚠️ Не удалось: ${e.message.split('\n')[0]}`);
    }
  }
  
  // Находим карточку дронов
  let droneCardIndex = -1;
  for (let i = 0; i < cardCount; i++) {
    const text = await allCards.nth(i).textContent();
    if (text.includes('Обработка снимков с дрона')) {
      droneCardIndex = i;
      break;
    }
  }
  
  if (droneCardIndex >= 0) {
    const droneCard = allCards.nth(droneCardIndex);
    
    // Dropdown культур
    const cropSelect = page.locator('#drone-crop-type');
    const isCropVisible = await cropSelect.isVisible();
    console.log(`🌾 Dropdown культур виден: ${isCropVisible}`);
    
    if (isCropVisible) {
      await cropSelect.screenshot({ path: 'e2e/results/drone_crop_select.png', force: true });
    }
    
    // Dropdown полей
    const fieldSelect = page.locator('#drone-field-select');
    const isFieldVisible = await fieldSelect.isVisible();
    console.log(`📋 Dropdown полей виден: ${isFieldVisible}`);
    
    if (isFieldVisible) {
      await fieldSelect.screenshot({ path: 'e2e/results/drone_field_select.png', force: true });
    }
  }
  
  // Тёмная тема - скроллим вверх сначала
  console.log('🌙 Переключение на тёмную тему...');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  
  const themeToggle = page.locator('#theme-toggle-btn');
  const isThemeVisible = await themeToggle.isVisible();
  console.log(`Кнопка темы видна: ${isThemeVisible}`);
  
  if (isThemeVisible) {
    await themeToggle.click();
    await page.waitForTimeout(1000);
    
    const html = page.locator('html');
    const theme = await html.getAttribute('data-theme');
    console.log(`Текущая тема: ${theme}`);
    
    if (theme === 'dark') {
      await page.screenshot({ path: 'e2e/results/uploads_page_dark_theme.png', fullPage: true });
    }
  }
  
  // Мобильная версия
  console.log('📱 Мобильная версия...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('http://localhost:8888/#uploads', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  
  await page.screenshot({ path: 'e2e/results/uploads_page_mobile.png', fullPage: true });
  
  await browser.close();
  
  console.log('');
  console.log('✅ Все скриншоты сделаны!');
  console.log('📁 Скриншоты в e2e/results/:');
  console.log('   - uploads_page_full.png');
  console.log('   - upload_card_0_*.png, upload_card_1_*.png, upload_card_2_*.png');
  console.log('   - drone_crop_select.png');
  console.log('   - drone_field_select.png');
  console.log('   - uploads_page_dark_theme.png');
  console.log('   - uploads_page_mobile.png');
})();
