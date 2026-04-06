/**
 * Упрощённый тест UI с автоматическим закрытием sidebar
 */

const { chromium } = require('playwright');

(async () => {
  console.log('🚀 Запуск...');
  
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  
  const page = await context.newPage();
  
  // Логирование ошибок
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));
  
  console.log('📸 Главная страница...');
  await page.goto('http://localhost:8888', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);
  
  // Закрываем sidebar
  console.log('🚪 Закрытие sidebar...');
  const sidebar = page.locator('#sidebar');
  if (await sidebar.isVisible()) {
    await page.locator('#sidebar-toggle').click();
    await page.waitForTimeout(500);
  }
  
  await page.screenshot({ path: 'e2e/results/review_main.png' });
  console.log('✓ Скриншот: review_main.png');
  
  // Переход в Загрузки через hash
  console.log('📥 Переход в Загрузки...');
  await page.evaluate(() => window.location.hash = '#uploads');
  await page.waitForTimeout(2000);
  
  await page.screenshot({ path: 'e2e/results/review_uploads.png' });
  console.log('✓ Скриншот: review_uploads.png');
  
  // Анализируем карточки
  const cards = page.locator('.upload-card');
  const count = await cards.count();
  console.log(`\n📦 Карточек найдено: ${count}`);
  
  for (let i = 0; i < count; i++) {
    const card = cards.nth(i);
    const title = await card.locator('h3').textContent();
    const desc = await card.locator('.upload-description').textContent();
    console.log(`\n${i + 1}. ${title.trim()}`);
    console.log(`   ${desc.trim()}`);
    
    await card.screenshot({ path: `e2e/results/review_card_${i}.png`, force: true });
    console.log(`   ✓ Скриншот: review_card_${i}.png`);
  }
  
  // Проверяем форму дронов
  console.log('\n🛸 Анализ формы загрузки дронов:');
  const cropSelect = page.locator('#drone-crop-type');
  const options = await cropSelect.locator('option').all();
  console.log(`   Опций культур: ${options.length}`);
  
  const fieldSelect = page.locator('#drone-field-select');
  const fieldOptions = await fieldSelect.locator('option').all();
  console.log(`   Опций полей: ${fieldOptions.length}`);
  
  // Проверяем ошибки консоли
  console.log('\n⚠️ Ошибки в консоли:');
  if (errors.length === 0) {
    console.log('   Нет ошибок! ✓');
  } else {
    errors.forEach(err => console.log(`   ❌ ${err}`));
  }
  
  // Тёмная тема
  console.log('\n🌙 Тёмная тема...');
  await page.evaluate(() => window.location.hash = '#map');
  await page.waitForTimeout(500);
  await page.locator('#theme-toggle-btn').click();
  await page.waitForTimeout(1000);
  
  const theme = await page.locator('html').getAttribute('data-theme');
  console.log(`   Тема: ${theme}`);
  
  await page.screenshot({ path: 'e2e/results/review_dark.png' });
  console.log('✓ Скриншот: review_dark.png');
  
  // Мобильная версия
  console.log('\n📱 Мобильная версия...');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('http://localhost:8888', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  
  await page.screenshot({ path: 'e2e/results/review_mobile.png' });
  console.log('✓ Скриншот: review_mobile.png');
  
  await browser.close();
  
  console.log('\n✅ Готово!');
  console.log('\n📁 Все скриншоты в e2e/results/:');
  console.log('   review_main.png       — главная страница');
  console.log('   review_uploads.png    — страница загрузок');
  console.log('   review_card_0.png     — карточка Shapefile');
  console.log('   review_card_1.png     — карточка дронов');
  console.log('   review_card_2.png     — карточка NDVI');
  console.log('   review_dark.png       — тёмная тема');
  console.log('   review_mobile.png     — мобильная версия');
})();
