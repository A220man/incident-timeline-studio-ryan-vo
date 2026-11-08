"""Test script to verify tags are included in CSV export."""
import sys
sys.path.insert(0, '/var/lib/alan-portfolio/workspaces/ryan/incident-timeline-studio-ryan-vo')

from backend.app.services.export import timeline_csv

# Test events with tags
events = [
    {
        'id': 'evt-1',
        'timestamp': '2026-10-09T12:00:00Z',
        'source': 'auth',
        'severity': 'high',
        'message': 'Failed login',
        'actor': 'alice',
        'host': 'server1',
        'ip': '192.0.2.1',
        'fingerprint': 'fp-1',
        'review_status': 'relevant',
        'review_note': 'Suspicious',
        'reviewed_by': 'analyst1',
        'tags': ['credential-access', 'brute-force']
    },
    {
        'id': 'evt-2',
        'timestamp': '2026-10-09T12:01:00Z',
        'source': 'network',
        'severity': 'medium',
        'message': 'Port scan',
        'actor': 'bob',
        'host': 'server2',
        'ip': '192.0.2.2',
        'fingerprint': 'fp-2',
        'review_status': 'unreviewed',
        'review_note': '',
        'reviewed_by': '',
        'tags': []
    },
    {
        'id': 'evt-3',
        'timestamp': '2026-10-09T12:02:00Z',
        'source': 'dns',
        'severity': 'low',
        'message': 'DNS query',
        'actor': 'charlie',
        'host': 'server3',
        'ip': '192.0.2.3',
        'fingerprint': 'fp-3',
        'review_status': 'benign',
        'review_note': 'Normal traffic',
        'reviewed_by': 'analyst2',
        'tags': ['reconnaissance']
    },
]

csv_output = timeline_csv(events)
print("CSV Output:")
print(csv_output)

# Verify tags column exists
lines = csv_output.strip().split('\n')
header = lines[0]
print(f"\nHeader: {header}")
assert 'tags' in header, "tags column missing from header"

# Check first event has tags
row1 = lines[1]
print(f"Row 1: {row1}")
assert 'credential-access;brute-force' in row1, "tags not found in row 1"

# Check second event has empty tags
row2 = lines[2]
print(f"Row 2: {row2}")
assert row2.endswith(','), "empty tags not handled correctly" or row2.endswith('""')

# Check third event has single tag
row3 = lines[3]
print(f"Row 3: {row3}")
assert 'reconnaissance' in row3, "single tag not found in row 3"

print("\n✅ All tests passed!")

