import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { Timeline } from '../components/Timeline';
import type { Page, Event } from '../types';

test('renders severity filter and fires onSeverity on change', () => {
  const onSeverity = vi.fn();
  const sampleData: Page<Event> = {
    items: [
      {
        id: 'ev-1',
        incident_id: 'inc-1',
        import_id: 'imp-1',
        timestamp: '2026-10-09T12:00:00Z',
        original_timestamp: '2026-10-09T12:00:00Z',
        source: 'auth',
        message: 'Suspicious login',
        severity: 'critical',
        actor: 'admin',
        host: 'dc-01',
        ip: '10.0.0.1',
        fingerprint: 'fp-1',
        raw_sha256: 'sha-1',
        row_number: 1,
        review_status: 'unreviewed',
        review_note: '',
        reviewed_by: '',
        version: 1,
      },
    ],
    total: 1,
  };

  render(
    <Timeline
      id="inc-1"
      data={sampleData}
      offset={0}
      onOffset={() => {}}
      query=""
      onQuery={() => {}}
      status=""
      onStatus={() => {}}
      severity=""
      onSeverity={onSeverity}
      component=""
      onComponent={() => {}}
      components={[]}
      disabled={false}
      onSaved={() => {}}
    />
  );

  const select = screen.getByLabelText('Severity filter');
  expect(select).toBeInTheDocument();
  expect(screen.getByText('Suspicious login')).toBeInTheDocument();

  fireEvent.change(select, { target: { value: 'critical' } });
  expect(onSeverity).toHaveBeenCalledWith('critical');
});