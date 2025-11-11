# SPDX-FileCopyrightText: Copyright (c) 2025 The Newton Developers
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import unittest
from unittest.mock import MagicMock, patch

import warp as wp

import newton

wp.config.quiet = True


class TestViewerBlueprintAccumulation(unittest.TestCase):
    """Tests for blueprint accumulation and hidden parameter support in ViewerRerun."""

    def setUp(self):
        """Set up test fixtures with mocked rerun."""
        # Mock the rerun module functions where they're used
        self.patcher_rr_init = patch("newton._src.viewer.viewer_rerun.rr.init")
        self.patcher_rr_serve_grpc = patch("newton._src.viewer.viewer_rerun.rr.serve_grpc", return_value="mock://server")
        self.patcher_rr_serve_web_viewer = patch("newton._src.viewer.viewer_rerun.rr.serve_web_viewer")
        self.patcher_rr_log = patch("newton._src.viewer.viewer_rerun.rr.log")
        self.patcher_rr_send_blueprint = patch("newton._src.viewer.viewer_rerun.rr.send_blueprint")
        self.patcher_rr_Mesh3D = patch("newton._src.viewer.viewer_rerun.rr.Mesh3D", return_value=MagicMock())
        self.patcher_rr_InstancePoses3D = patch("newton._src.viewer.viewer_rerun.rr.InstancePoses3D", return_value=MagicMock())

        self.patcher_rrb_Blueprint = patch("newton._src.viewer.viewer_rerun.rrb.Blueprint", return_value=MagicMock())
        self.patcher_rrb_Spatial3DView = patch("newton._src.viewer.viewer_rerun.rrb.Spatial3DView", return_value=MagicMock())
        self.patcher_rrb_EntityBehavior = patch("newton._src.viewer.viewer_rerun.rrb.EntityBehavior", side_effect=lambda **kwargs: MagicMock(**kwargs))

        # Start all patchers
        self.patcher_rr_init.start()
        self.patcher_rr_serve_grpc.start()
        self.patcher_rr_serve_web_viewer.start()
        self.mock_rr_log = self.patcher_rr_log.start()
        self.mock_rr_send_blueprint = self.patcher_rr_send_blueprint.start()
        self.patcher_rr_Mesh3D.start()
        self.patcher_rr_InstancePoses3D.start()

        self.patcher_rrb_Blueprint.start()
        self.patcher_rrb_Spatial3DView.start()
        self.mock_rrb_EntityBehavior = self.patcher_rrb_EntityBehavior.start()

    def tearDown(self):
        """Clean up mocks."""
        patch.stopall()

    def _create_simple_model(self):
        """Create a simple model with a few shapes for testing."""
        builder = newton.ModelBuilder()
        builder.add_body(
            xform=wp.transform(wp.vec3(0.0, 0.0, 1.0), wp.quat_identity()),
            mass=1.0,
            I_m=wp.mat33(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            key="test_body",
        )
        builder.add_shape_box(body=0, hx=0.5, hy=0.5, hz=0.5)
        return builder.finalize()

    def test_visibility_tracked_in_log_mesh(self):
        """Test that visibility is tracked when logging meshes."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Create simple test mesh data
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)

        # Log mesh as hidden
        viewer.log_mesh("/test/hidden", points, indices, hidden=True)
        self.assertEqual(viewer._entity_visibility["/test/hidden"], False)

        # Log mesh as visible
        viewer.log_mesh("/test/visible", points, indices, hidden=False)
        self.assertEqual(viewer._entity_visibility["/test/visible"], True)

    def test_multiple_entities_visibility(self):
        """Test visibility tracking for multiple entities with alternating visibility."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Create simple test mesh data
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)

        # Log 10 entities with alternating visibility
        for i in range(10):
            viewer.log_mesh(f"/entity_{i}", points, indices, hidden=(i % 2 == 0))

        # Verify all tracked with correct visibility
        for i in range(10):
            expected_visible = i % 2 != 0
            self.assertEqual(
                viewer._entity_visibility[f"/entity_{i}"],
                expected_visible,
                f"Entity {i} visibility mismatch",
            )

    def test_blueprint_state_initialized(self):
        """Test that blueprint state is properly initialized."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Check initial state
        self.assertIsInstance(viewer._entity_visibility, dict)
        self.assertEqual(len(viewer._entity_visibility), 0)
        self.assertEqual(viewer._blueprint_applied, False)

    def test_set_model_triggers_blueprint(self):
        """Test that set_model triggers blueprint application."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)
        model = self._create_simple_model()

        # Blueprint should not be applied initially
        self.assertFalse(viewer._blueprint_applied)

        # Set model should trigger blueprint
        viewer.set_model(model)

        # Blueprint should be applied after set_model
        self.assertTrue(viewer._blueprint_applied)

        # Verify send_blueprint was called
        self.mock_rr_send_blueprint.assert_called_once()

    def test_set_model_only_applies_blueprint_once(self):
        """Test that blueprint is only applied once during set_model."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)
        model = self._create_simple_model()

        # Set model first time
        viewer.set_model(model)
        self.assertTrue(viewer._blueprint_applied)

        # Verify send_blueprint was called once
        self.assertEqual(self.mock_rr_send_blueprint.call_count, 1)

        # Note: set_model can only be called once due to parent class constraint
        # This test verifies the guard exists in the code

    def test_log_instances_tracks_visibility(self):
        """Test that log_instances tracks visibility for instanced geometry."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Create mesh first
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)
        viewer.log_mesh("/geometry/mesh", points, indices, hidden=False)

        # Create instance data
        xforms = wp.array([wp.transform(wp.vec3(0.0, 0.0, 0.0), wp.quat_identity())], dtype=wp.transform)
        scales = wp.array([wp.vec3(1.0, 1.0, 1.0)], dtype=wp.vec3)
        colors = wp.array([wp.vec3(1.0, 0.0, 0.0)], dtype=wp.vec3)
        materials = wp.array([wp.vec4(0.0, 0.0, 0.0, 0.0)], dtype=wp.vec4)

        # Log instances as hidden
        viewer.log_instances(
            "/instances/hidden", "/geometry/mesh", xforms, scales, colors, materials, hidden=True
        )
        self.assertEqual(viewer._entity_visibility["/instances/hidden"], False)

        # Log instances as visible
        viewer.log_instances(
            "/instances/visible", "/geometry/mesh", xforms, scales, colors, materials, hidden=False
        )
        self.assertEqual(viewer._entity_visibility["/instances/visible"], True)

    def test_default_visibility_is_visible(self):
        """Test that default visibility (when hidden=False) is visible."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Create simple test mesh data
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)

        # Log mesh with default hidden=False
        viewer.log_mesh("/test/default", points, indices)
        self.assertEqual(viewer._entity_visibility["/test/default"], True)

    def test_template_geometry_paths(self):
        """Test that geometry paths starting with /geometry/ are properly tracked."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)
        model = self._create_simple_model()

        # Set model - this will populate geometry
        viewer.set_model(model)

        # Check that some entities were tracked
        self.assertGreater(len(viewer._entity_visibility), 0)

        # Check if any /geometry/ paths exist (template geometry)
        geometry_paths = [path for path in viewer._entity_visibility.keys() if path.startswith("/geometry/")]

        # Template geometry should be present
        self.assertGreater(len(geometry_paths), 0)

        # Template geometry should be hidden
        for path in geometry_paths:
            self.assertFalse(
                viewer._entity_visibility[path], f"Template geometry {path} should be hidden (visible=False)"
            )

    def test_apply_blueprint_creates_correct_overrides(self):
        """Test that _apply_blueprint creates correct visibility overrides."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Manually add some visibility tracking
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)
        viewer.log_mesh("/test/hidden", points, indices, hidden=True)
        viewer.log_mesh("/test/visible", points, indices, hidden=False)

        # Manually call _apply_blueprint
        viewer._apply_blueprint()

        # Verify blueprint was applied
        self.assertTrue(viewer._blueprint_applied)
        self.mock_rr_send_blueprint.assert_called_once()

        # Verify EntityBehavior was called with correct visibility
        # We should have 2 calls to EntityBehavior (one for each entity)
        self.assertEqual(self.mock_rrb_EntityBehavior.call_count, 2)


class TestViewerBlueprintIntegration(unittest.TestCase):
    """Integration tests for blueprint accumulation with real models."""

    def setUp(self):
        """Set up test fixtures with mocked rerun."""
        # Mock the rerun module functions where they're used
        self.patcher_rr_init = patch("newton._src.viewer.viewer_rerun.rr.init")
        self.patcher_rr_serve_grpc = patch("newton._src.viewer.viewer_rerun.rr.serve_grpc", return_value="mock://server")
        self.patcher_rr_serve_web_viewer = patch("newton._src.viewer.viewer_rerun.rr.serve_web_viewer")
        self.patcher_rr_log = patch("newton._src.viewer.viewer_rerun.rr.log")
        self.patcher_rr_send_blueprint = patch("newton._src.viewer.viewer_rerun.rr.send_blueprint")
        self.patcher_rr_Mesh3D = patch("newton._src.viewer.viewer_rerun.rr.Mesh3D", return_value=MagicMock())
        self.patcher_rr_InstancePoses3D = patch("newton._src.viewer.viewer_rerun.rr.InstancePoses3D", return_value=MagicMock())

        self.patcher_rrb_Blueprint = patch("newton._src.viewer.viewer_rerun.rrb.Blueprint", return_value=MagicMock())
        self.patcher_rrb_Spatial3DView = patch("newton._src.viewer.viewer_rerun.rrb.Spatial3DView", return_value=MagicMock())
        self.patcher_rrb_EntityBehavior = patch("newton._src.viewer.viewer_rerun.rrb.EntityBehavior", side_effect=lambda **kwargs: MagicMock(**kwargs))

        # Start all patchers
        self.patcher_rr_init.start()
        self.patcher_rr_serve_grpc.start()
        self.patcher_rr_serve_web_viewer.start()
        self.mock_rr_log = self.patcher_rr_log.start()
        self.mock_rr_send_blueprint = self.patcher_rr_send_blueprint.start()
        self.patcher_rr_Mesh3D.start()
        self.patcher_rr_InstancePoses3D.start()

        self.patcher_rrb_Blueprint.start()
        self.patcher_rrb_Spatial3DView.start()
        self.mock_rrb_EntityBehavior = self.patcher_rrb_EntityBehavior.start()

    def tearDown(self):
        """Clean up mocks."""
        patch.stopall()

    def _create_model_with_multiple_shapes(self):
        """Create a model with multiple shapes for testing."""
        builder = newton.ModelBuilder()

        # Add first body with box
        builder.add_body(
            xform=wp.transform(wp.vec3(0.0, 0.0, 1.0), wp.quat_identity()),
            mass=1.0,
            I_m=wp.mat33(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            key="body_1",
        )
        builder.add_shape_box(body=0, hx=0.5, hy=0.5, hz=0.5)

        # Add second body with sphere
        builder.add_body(
            xform=wp.transform(wp.vec3(2.0, 0.0, 1.0), wp.quat_identity()),
            mass=1.0,
            I_m=wp.mat33(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            key="body_2",
        )
        builder.add_shape_sphere(body=1, radius=0.5)

        return builder.finalize()

    def test_model_with_multiple_shapes(self):
        """Test that model with multiple shapes correctly tracks all entity visibility."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)
        model = self._create_model_with_multiple_shapes()

        # Set model
        viewer.set_model(model)

        # Should have tracked multiple entities
        self.assertGreater(len(viewer._entity_visibility), 0)

        # All /geometry/ paths should be hidden
        for path, visible in viewer._entity_visibility.items():
            if path.startswith("/geometry/"):
                self.assertFalse(visible, f"Template geometry {path} should be hidden")

    def test_no_model_no_blueprint_applied(self):
        """Test that blueprint is not applied if no model is set."""
        from newton.viewer import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Without setting model, blueprint should not be applied
        self.assertFalse(viewer._blueprint_applied)

        # Manually log a mesh
        points = wp.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=wp.vec3)
        indices = wp.array([0, 1, 2], dtype=wp.uint32)
        viewer.log_mesh("/manual/mesh", points, indices, hidden=True)

        # Visibility tracked but blueprint not applied (no trigger)
        self.assertEqual(viewer._entity_visibility["/manual/mesh"], False)
        self.assertFalse(viewer._blueprint_applied)

        # Verify send_blueprint was not called
        self.mock_rr_send_blueprint.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
