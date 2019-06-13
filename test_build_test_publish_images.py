import unittest

from unittest import mock

import build_test_publish_images


class TestBuildPublishAmis(unittest.TestCase):

    def setUp(self):
        self._build_dir = "some-dir"
        self._dry_run = True
        self._tests = ["test_one", "test_two"]
        self._publish_step = build_test_publish_images.PUBLISH_STEP_INTEGRATION_TESTS
        self._tf_build_dir = "some-dir/temp"
        self._run_integration_tests = True
        self._run_framework_tests = True
        self._ssh_user = 'centos'

    @mock.patch("build_test_publish_images.shutil")
    @mock.patch("build_test_publish_images.setup_cluster_and_test")
    @mock.patch("build_test_publish_images.setup_terraform")
    @mock.patch("build_test_publish_images.packer_validate_and_build")
    @mock.patch("build_test_publish_images.get_tf_build_dir")
    @mock.patch("build_test_publish_images.get_ssh_user_from_packer_json", new_callable=lambda: lambda _: 'centos')
    def test_execute_qualification_process(
            self,
            mock_get_ssh_user_from_packer_json,
            mock_tf_build_dir,
            mock_packer_validate_and_build,
            mock_setup_terraform,
            mock_setup_cluster_and_test,
            mock_shutil):

        mock_tf_build_dir.return_value = self._tf_build_dir

        build_test_publish_images.execute_qualification_process(
            self._build_dir,
            self._dry_run,
            self._tests,
            self._publish_step,
            self._run_integration_tests,
            self._run_framework_tests)

        mock_packer_validate_and_build.assert_called_with(self._build_dir, self._dry_run, self._publish_step)
        mock_setup_terraform.assert_called_with(self._build_dir, self._tf_build_dir, self._ssh_user)

        mock_setup_cluster_and_test.assert_called_with(
                self._build_dir,
                self._tf_build_dir,
                self._dry_run,
                self._tests,
                self._publish_step,
                self._run_integration_tests,
                self._run_framework_tests,
                self._ssh_user)

        mock_shutil.rmtree.assert_called_with(self._tf_build_dir, ignore_errors=True)

    @mock.patch("build_test_publish_images.shutil")
    @mock.patch("build_test_publish_images.setup_cluster_and_test")
    @mock.patch("build_test_publish_images.setup_terraform")
    @mock.patch("build_test_publish_images.packer_validate_and_build")
    @mock.patch("build_test_publish_images.get_tf_build_dir")
    @mock.patch("build_test_publish_images.get_ssh_user_from_packer_json", new_callable=lambda: lambda _: 'centos')
    def test_execute_qualification_process_terraform_setup_error(
            self,
            mock_get_ssh_user_from_packer_json,
            mock_tf_build_dir,
            mock_packer_validate_and_build,
            mock_setup_terraform,
            mock_setup_cluster_and_test,
            mock_shutil):

        mock_tf_build_dir.return_value = self._tf_build_dir
        mock_setup_terraform.side_effect = ValueError("Error during terraform setup.")

        try:
            build_test_publish_images.execute_qualification_process(
                self._build_dir,
                self._dry_run,
                self._tests,
                self._publish_step,
                self._run_integration_tests,
                self._run_framework_tests)
            self.fail("ValueError was not raised during terraform setup.")
        except ValueError:
            pass

        mock_packer_validate_and_build.assert_called_with(self._build_dir, self._dry_run, self._publish_step)
        self.assertFalse(mock_setup_cluster_and_test.called)

        mock_shutil.rmtree.assert_called_with(self._tf_build_dir, ignore_errors=True)

    @mock.patch("build_test_publish_images.shutil")
    @mock.patch("build_test_publish_images.setup_cluster_and_test")
    @mock.patch("build_test_publish_images.setup_terraform")
    @mock.patch("build_test_publish_images.packer_validate_and_build")
    @mock.patch("build_test_publish_images.get_tf_build_dir")
    @mock.patch("build_test_publish_images.get_ssh_user_from_packer_json", new_callable=lambda: lambda _: 'centos')
    def test_execute_qualification_process_terraform_cluster_launch_error(
            self,
            mock_get_ssh_user_from_packer_json,
            mock_tf_build_dir,
            mock_packer_validate_and_build,
            mock_setup_terraform,
            mock_setup_cluster_and_test,
            mock_shutil):

        mock_tf_build_dir.return_value = self._tf_build_dir
        mock_setup_cluster_and_test.side_effect = Exception("Error during cluster setup.")

        try:
            build_test_publish_images.execute_qualification_process(
                self._build_dir,
                self._dry_run,
                self._tests,
                self._publish_step,
                self._run_integration_tests,
                self._run_framework_tests)
            self.fail("No error raised during cluster setup.")
        except Exception:
            pass

        mock_packer_validate_and_build.assert_called_with(self._build_dir, self._dry_run, self._publish_step)
        mock_setup_terraform.assert_called_with(self._build_dir, self._tf_build_dir, 'centos')

        mock_setup_cluster_and_test.assert_called_with(
                self._build_dir,
                self._tf_build_dir,
                self._dry_run,
                self._tests,
                self._publish_step,
                self._run_integration_tests,
                self._run_framework_tests,
                self._ssh_user)

        mock_shutil.rmtree.assert_called_with(self._tf_build_dir, ignore_errors=True)
