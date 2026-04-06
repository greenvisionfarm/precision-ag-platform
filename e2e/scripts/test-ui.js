/**
 * Тест UI с проверкой консоли и скриншотами
 */

const { chromium } = require('playwright');

(async () => {
  console.log('🚀 Запуск браузера...');
  
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  
  const page = await context.newPage();
  
  // Логирование ошибок консоли
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`❌ Console Error: ${msg.text()}`);
    }
  });
  
  page.on('pageerror', error => {
    console.log(`❌ Page Error: ${error.message}`);
  });
  
  console.log('📸 Переход на главную...');
  await page.goto('http://localhost:8888', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  
  console.log('📷 Скриншот главной страницы...');
  await page.screenshot({ path: 'e2e/results/ui_main_page.png' });
  
  // Проверяем наличие ошибки
  const errorToast = page.locator('.toast-error, .error-toast, [class*="error"]');
  const hasError = await errorToast.isVisible();
  console.log(`⚠️ Есть ошибка на странице: ${hasError}`);
  
  if (hasError) {
    const errorText = await errorToast.textContent();
    console.log(`   Текст ошибки: ${errorText}`);
  }
  
  // Клик на Загрузки
  console.log('📥 Переход в Загрузки...');
  await page.click('a[href="#uploads"]');
  await page.waitForTimeout(2000);
  
  console.log('📷 Скриншот страницы загрузок...');
  await page.screenshot({ path: 'e2e/results/ui_uploads_page.png' });
  
  // Находим карточки
  const cards = page.locator('.upload-card');
  const count = await cards.count();
  console.log(`📦 Найдено карточек: ${count}`);
  
  for (let i = 0; i < count; i++) {
    const card = cards.nth(i);
    const title = await card.locator('h3').textContent();
    console.log(`  ${i}: ${title.trim()}`);
    
    // Скриншот каждой карточки
    await card.screenshot({ path: `e2e/results/ui_card_${i}.png`, force: true });
  }
  
  // Проверяем форму загрузки дронов
  console.log('🛸 Проверка формы дронов...');
  const droneForm = page.locator('#drone-upload-form');
  const isDroneFormVisible = await droneForm.isVisible();
  console.log(`   Форма видна: ${isDroneFormVisible}`);
  
  if (isDroneFormVisible) {
    // Проверяем dropdown культур
    const cropSelect = page.locator('#drone-crop-type');
    const cropOptions = await cropSelect.locator('option').all();
    console.log(`   🌾 Опций культур: ${cropOptions.length}`);
    
    // Проверяем dropdown полей
    const fieldSelect = page.locator('#drone-field-select');
    const fieldOptions = await fieldSelect.locator('option').all();
    console.log(`   📋 Опций полей: ${fieldOptions.length}`);
    
    // Скриншот формы
    await droneForm.screenshot({ path: 'e2e/results/ui_drone_form.png', force: true });
  }
  
  // Проверяем тёмную тему
  console.log('🌙 Переключение темы...');
  await page.click('#theme-toggle-btn');
  await page.waitForTimeout(1000);
  
  const html = page.locator('html');
  const theme = await html.getAttribute('data-theme');
  console.log(`   Тема: ${theme}`);
  
  await page.screenshot({ path: 'e2e/results/ui_dark_theme.png' });
  
  // Мобильная версия
  console.log('📱 Мобильная версия...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('http://localhost:8888', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  await page.screenshot({ path: 'e2e/results/ui_mobile.png' });
  
  // Проверяем мобильное меню
  const menuButton = page.locator('#sidebar-toggle');
  await menuButton.click();
  await page.waitForTimeout(500);
  
  await page.screenshot({ path: 'e2e/results/ui_mobile_menu.png' });
  
  await browser.close();
  
  console.log('');
  console.log('✅ Тест завершён!');
  console.log('📁 Скриншоты в e2e/results/:');
  console.log('   - ui_main_page.png');
  console.log('   - ui_uploads_page.png');
  console.log('   - ui_card_0.png, ui_card_1.png, ui_card_2.png');
  console.log('   - ui_drone_form.png');
  console.log('   - ui_dark_theme.png');
  console.log('   - ui_mobile.png');
  console.log('   - ui_mobile_menu.png');
})();
