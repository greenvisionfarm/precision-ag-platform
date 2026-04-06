/**
 * Простой скрипт для скриншотов
 * Запуск: node e2e/scripts/take-screenshots-simple.js
 */

const { chromium } = require('playwright');

(async () => {
  console.log('🚀 Запуск...');
  
  const browser = await chromium.launch({ 
    headless: true
  });
  
  const page = await browser.newPage();
  
  console.log('📸 Переход на страницу...');
  await page.goto('http://localhost:8888', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  
  console.log('📷 Скриншот главной...');
  await page.screenshot({ path: 'e2e/results/test_main.png' });
  
  // Кликаем на Загрузки в меню
  console.log('📥 Клик на Загрузки...');
  const uploadsLink = page.locator('a[href="#uploads"]');
  await uploadsLink.click();
  await page.waitForTimeout(3000);
  
  console.log('📷 Скриншот загрузок...');
  await page.screenshot({ path: 'e2e/results/test_uploads.png' });
  
  // Ищем карточки
  const cards = page.locator('.upload-card');
  const count = await cards.count();
  console.log(`📦 Карточек найдено: ${count}`);
  
  for (let i = 0; i < count; i++) {
    const title = await cards.nth(i).locator('h3').textContent();
    console.log(`  ${i}: ${title.trim()}`);
  }
  
  await browser.close();
  console.log('✅ Готово!');
})();
