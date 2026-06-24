/**
 * E2E тесты для миссий дронов.
 */
import { test, expect } from '../fixtures/fixtures';

function randomFieldGeometry() {
  const base = 48.0 + Math.random() * 0.05;
  const lon = 19.0 + Math.random() * 0.05;
  return {
    type: 'Polygon' as const,
    coordinates: [[[lon, base], [lon + 0.01, base], [lon + 0.01, base + 0.01], [lon, base + 0.01], [lon, base]]],
  };
}

test.describe('Миссии дронов', () => {
  test('создание миссии → получение пути → waypoints внутри поля', async ({ authedRequest }) => {
    const fieldResp = await authedRequest.post('/api/field/add', {
      data: { name: `MissField ${Date.now()}`, geometry: randomFieldGeometry() },
    });
    expect(fieldResp.ok(), `createField: ${await fieldResp.text()}`).toBeTruthy();
    const { id: fieldId } = await fieldResp.json();

    const createResp = await authedRequest.post(`/api/field/${fieldId}/missions/add`, {
      data: { name: 'E2E миссия', height: 100, overlap_h: 80, overlap_w: 70, direction: 0 },
    });
    expect(createResp.ok(), `createMission: ${await createResp.text()}`).toBeTruthy();
    const { id: missionId, status } = await createResp.json();
    expect(missionId).toBeTruthy();
    expect(status).toBe('created');

    const listResp = await authedRequest.get(`/api/field/${fieldId}/missions`);
    expect(listResp.ok(), `list: ${await listResp.text()}`).toBeTruthy();
    const { missions } = await listResp.json();
    expect(missions.length).toBeGreaterThan(0);

    const detailResp = await authedRequest.get(`/api/field/${fieldId}/missions/${missionId}`);
    expect(detailResp.ok(), `detail: ${await detailResp.text()}`).toBeTruthy();
    const detail = await detailResp.json();

    expect(detail.path.length).toBeGreaterThan(0);
    expect(detail.waypoint_count).toBeGreaterThan(0);
    expect(detail.height).toBe(100);

    for (const [lat, lon] of detail.path) {
      expect(typeof lat).toBe('number');
      expect(typeof lon).toBe('number');
      expect(isFinite(lat)).toBeTruthy();
      expect(isFinite(lon)).toBeTruthy();
    }

    await authedRequest.delete(`/api/field/delete/${fieldId}`);
  });

  test('preview возвращает путь без сохранения', async ({ authedRequest }) => {
    const fieldResp = await authedRequest.post('/api/field/add', {
      data: { name: `PreviewField ${Date.now()}`, geometry: randomFieldGeometry() },
    });
    const { id: fieldId } = await fieldResp.json();

    const previewResp = await authedRequest.post(`/api/field/${fieldId}/missions/preview`, {
      data: { height: 80, overlap_h: 80, overlap_w: 70, direction: 45 },
    });
    expect(previewResp.ok(), `preview: ${await previewResp.text()}`).toBeTruthy();
    const previewData = await previewResp.json();
    expect(previewData.path.length).toBeGreaterThan(0);

    const listResp = await authedRequest.get(`/api/field/${fieldId}/missions`);
    const { missions } = await listResp.json();
    expect(missions.length).toBe(0);

    await authedRequest.delete(`/api/field/delete/${fieldId}`);
  });

  test('разные углы курса дают разные пути', async ({ authedRequest }) => {
    const fieldResp = await authedRequest.post('/api/field/add', {
      data: { name: `DirField ${Date.now()}`, geometry: randomFieldGeometry() },
    });
    const { id: fieldId } = await fieldResp.json();

    const p0 = await authedRequest.post(`/api/field/${fieldId}/missions/preview`, {
      data: { height: 100, overlap_w: 70, direction: 0 },
    });
    expect(p0.ok(), `preview0: ${await p0.text()}`).toBeTruthy();
    const d0 = await p0.json();

    const p90 = await authedRequest.post(`/api/field/${fieldId}/missions/preview`, {
      data: { height: 100, overlap_w: 70, direction: 90 },
    });
    expect(p90.ok(), `preview90: ${await p90.text()}`).toBeTruthy();
    const d90 = await p90.json();

    expect(d0.path).not.toEqual(d90.path);

    await authedRequest.delete(`/api/field/delete/${fieldId}`);
  });

  test('удаление миссии', async ({ authedRequest }) => {
    const fieldResp = await authedRequest.post('/api/field/add', {
      data: { name: `DelField ${Date.now()}`, geometry: randomFieldGeometry() },
    });
    const { id: fieldId } = await fieldResp.json();

    const createResp = await authedRequest.post(`/api/field/${fieldId}/missions/add`, {
      data: { name: 'Для удаления', height: 100, overlap_w: 70 },
    });
    const { id: missionId } = await createResp.json();

    const deleteResp = await authedRequest.delete(`/api/field/${fieldId}/missions/${missionId}/delete`);
    expect(deleteResp.ok(), `delete: ${await deleteResp.text()}`).toBeTruthy();

    const getResp = await authedRequest.get(`/api/field/${fieldId}/missions/${missionId}`);
    expect(getResp.status()).toBe(404);

    await authedRequest.delete(`/api/field/delete/${fieldId}`);
  });
});
