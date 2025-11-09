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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied,
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest.mock import MagicMock, patch

import sys


class TestViewerRerunInit(unittest.TestCase):
    """Test suite for ViewerRerun.__init__ method."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock rerun module
        self.mock_rr = MagicMock()
        self.mock_rr.init = MagicMock()
        self.mock_rr.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        self.mock_rr.serve_web_viewer = MagicMock()
        self.mock_rr.disconnect = MagicMock()

    def tearDown(self):
        """Clean up after each test method."""
        # Remove any viewer instances from the module cache
        if "newton._src.viewer.viewer_rerun" in sys.modules:
            # Reset the module's rr to None to clean state
            pass

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_with_default_parameters(self, mock_rr_module):
        """Test successful initialization with default parameters."""
        # Configure mock
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        # Import and initialize
        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun()

        # Verify rr.init was called with default app_id
        mock_rr_module.init.assert_called_once_with("newton-viewer")

        # Verify server mode was enabled
        mock_rr_module.serve_grpc.assert_called_once()

        # Verify web viewer was launched
        mock_rr_module.serve_web_viewer.assert_called_once_with(connect_to="grpc://127.0.0.1:9876")

        # Verify internal state
        self.assertEqual(viewer.server, True)
        self.assertEqual(viewer.address, "127.0.0.1:9876")
        self.assertEqual(viewer.launch_viewer, True)
        self.assertEqual(viewer.app_id, "newton-viewer")
        self.assertEqual(viewer._running, True)
        self.assertIsNone(viewer._viewer_process)
        self.assertEqual(viewer._meshes, {})
        self.assertEqual(viewer._instances, {})

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_with_custom_app_id(self, mock_rr_module):
        """Test initialization with custom app_id."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun(app_id="my-custom-app")

        # Verify rr.init was called with custom app_id
        mock_rr_module.init.assert_called_once_with("my-custom-app")
        self.assertEqual(viewer.app_id, "my-custom-app")

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_server_false_launch_viewer_false(self, mock_rr_module):
        """Test initialization with server=False and launch_viewer=False."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock()
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun(server=False, launch_viewer=False)

        # Verify rr.init was called
        mock_rr_module.init.assert_called_once_with("newton-viewer")

        # Verify serve_grpc was NOT called
        mock_rr_module.serve_grpc.assert_not_called()

        # Verify serve_web_viewer was NOT called
        mock_rr_module.serve_web_viewer.assert_not_called()

        # Verify internal state
        self.assertEqual(viewer.server, False)
        self.assertEqual(viewer.launch_viewer, False)

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_server_true_launch_viewer_false(self, mock_rr_module):
        """Test initialization with server=True and launch_viewer=False."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun(server=True, launch_viewer=False)

        # Verify rr.init was called
        mock_rr_module.init.assert_called_once_with("newton-viewer")

        # Verify serve_grpc WAS called
        mock_rr_module.serve_grpc.assert_called_once()

        # Verify serve_web_viewer was NOT called
        mock_rr_module.serve_web_viewer.assert_not_called()

        # Verify internal state
        self.assertEqual(viewer.server, True)
        self.assertEqual(viewer.launch_viewer, False)

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_server_false_launch_viewer_true_bug(self, mock_rr_module):
        """Test the bug: server=False, launch_viewer=True causes UnboundLocalError."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock()
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        # This should raise UnboundLocalError because server_uri is not defined
        # when server=False but launch_viewer=True tries to use it
        with self.assertRaises(UnboundLocalError) as context:
            ViewerRerun(server=False, launch_viewer=True)

        self.assertIn("server_uri", str(context.exception))

    @patch("newton._src.viewer.viewer_rerun.rr", None)
    def test_init_import_error_when_rerun_not_installed(self):
        """Test ImportError is raised when rerun is not installed."""
        from newton._src.viewer.viewer_rerun import ViewerRerun

        # Should raise ImportError with helpful message
        with self.assertRaises(ImportError) as context:
            ViewerRerun()

        self.assertIn("rerun package is required", str(context.exception))
        self.assertIn("pip install rerun-sdk", str(context.exception))

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_custom_address_parameter_stored(self, mock_rr_module):
        """Test that custom address parameter is stored correctly."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://192.168.1.100:8080")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        custom_address = "192.168.1.100:8080"
        viewer = ViewerRerun(address=custom_address)

        # Verify address is stored
        self.assertEqual(viewer.address, custom_address)

        # Note: address parameter is stored but not actually used in the current implementation
        # This is a limitation/bug in the existing code

    @patch("newton._src.viewer.viewer_rerun.ViewerBase.__init__")
    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_calls_parent_class_init(self, mock_rr_module, mock_parent_init):
        """Test that ViewerBase.__init__() is called via super()."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun()

        # Verify parent class __init__ was called
        mock_parent_init.assert_called_once()

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_all_parameters_custom(self, mock_rr_module):
        """Test initialization with all custom parameters."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://10.0.0.1:7777")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun(
            server=True, address="10.0.0.1:7777", launch_viewer=True, app_id="test-app-123"
        )

        # Verify all parameters
        self.assertEqual(viewer.server, True)
        self.assertEqual(viewer.address, "10.0.0.1:7777")
        self.assertEqual(viewer.launch_viewer, True)
        self.assertEqual(viewer.app_id, "test-app-123")

        # Verify correct calls
        mock_rr_module.init.assert_called_once_with("test-app-123")
        mock_rr_module.serve_grpc.assert_called_once()
        mock_rr_module.serve_web_viewer.assert_called_once_with(connect_to="grpc://10.0.0.1:7777")

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_internal_state_initialization(self, mock_rr_module):
        """Test that all internal state variables are initialized correctly."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun()

        # Verify all internal state
        self.assertTrue(hasattr(viewer, "_running"))
        self.assertEqual(viewer._running, True)

        self.assertTrue(hasattr(viewer, "_viewer_process"))
        self.assertIsNone(viewer._viewer_process)

        self.assertTrue(hasattr(viewer, "_meshes"))
        self.assertIsInstance(viewer._meshes, dict)
        self.assertEqual(len(viewer._meshes), 0)

        self.assertTrue(hasattr(viewer, "_instances"))
        self.assertIsInstance(viewer._instances, dict)
        self.assertEqual(len(viewer._instances), 0)


class TestViewerRerunInitParameterValidation(unittest.TestCase):
    """Additional tests for parameter validation and edge cases."""

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_server_parameter_types(self, mock_rr_module):
        """Test that server parameter accepts boolean values."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        # Test with True
        viewer1 = ViewerRerun(server=True)
        self.assertEqual(viewer1.server, True)

        # Test with False
        viewer2 = ViewerRerun(server=False, launch_viewer=False)
        self.assertEqual(viewer2.server, False)

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_address_parameter_types(self, mock_rr_module):
        """Test that address parameter accepts string values."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        # Test with various address formats
        addresses = [
            "127.0.0.1:9876",
            "localhost:8080",
            "192.168.1.100:7777",
            "my-server.example.com:9999",
        ]

        for addr in addresses:
            with self.subTest(address=addr):
                viewer = ViewerRerun(address=addr, launch_viewer=False)
                self.assertEqual(viewer.address, addr)

    @patch("newton._src.viewer.viewer_rerun.rr")
    def test_init_app_id_none_uses_default(self, mock_rr_module):
        """Test that app_id=None uses the default 'newton-viewer'."""
        mock_rr_module.init = MagicMock()
        mock_rr_module.serve_grpc = MagicMock(return_value="grpc://127.0.0.1:9876")
        mock_rr_module.serve_web_viewer = MagicMock()

        from newton._src.viewer.viewer_rerun import ViewerRerun

        viewer = ViewerRerun(app_id=None)

        self.assertEqual(viewer.app_id, "newton-viewer")
        mock_rr_module.init.assert_called_once_with("newton-viewer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
