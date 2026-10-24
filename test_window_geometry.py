"""Window placement stays usable after high-DPI and work-area changes."""
import json,tempfile,unittest
from pathlib import Path
from windows_app import visible_window_bounds,load_preferences

class WindowGeometryTests(unittest.TestCase):
 def test_large_compact_window_fits_short_high_dpi_screen(self):
  self.assertEqual(visible_window_bounds((150,50,840,1580),(0,0,1920,1104)),(150,0,840,1104))
 def test_large_full_window_fits_width_and_height(self):
  self.assertEqual(visible_window_bounds((100,100,2400,1800),(0,0,1920,1104)),(0,0,1920,1104))
 def test_monitor_left_of_primary_keeps_negative_coordinates(self):
  self.assertEqual(visible_window_bounds((-2300,80,900,900),(-1920,40,1920,1040)),(-1920,80,900,900))
 def test_disconnected_monitor_position_returns_inside_available_area(self):
  self.assertEqual(visible_window_bounds((2500,-900,900,700),(0,40,1920,1040)),(1020,40,900,700))
 def test_existing_visible_window_is_not_changed(self):
  bounds=(200,90,420,790)
  self.assertEqual(visible_window_bounds(bounds,(0,40,1920,1040)),bounds)
 def test_short_saved_full_view_is_restored(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'window.json';path.write_text(json.dumps({'full_size':[900,580]}))
   self.assertEqual(load_preferences(path)['full_size'],[900,580])
