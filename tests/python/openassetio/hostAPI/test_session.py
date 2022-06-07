#
#   Copyright 2013-2021 The Foundry Visionmongers Ltd
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Tests that cover the openassetio.hostAPI.Session class.
"""

# pylint: disable=no-self-use
# pylint: disable=invalid-name,redefined-outer-name
# pylint: disable=missing-class-docstring,missing-function-docstring

from unittest import mock

import pytest

from openassetio import constants, exceptions, log, Context, TraitsData
from openassetio.hostAPI import Session, HostInterface, Manager, ManagerFactoryInterface


@pytest.fixture
def mock_host_interface():
    return mock.create_autospec(spec=HostInterface)


@pytest.fixture
def mock_manager_factory(mock_manager_interface):
    factory = mock.create_autospec(spec=ManagerFactoryInterface)
    factory.instantiate.return_value = mock_manager_interface
    return factory


@pytest.fixture
def mock_logger():
    return mock.create_autospec(spec=log.LoggerInterface)


@pytest.fixture
def a_session(mock_host_interface, mock_logger, mock_manager_factory):
    return Session(mock_host_interface, mock_logger, mock_manager_factory)


class Test_Session_init:

    def test_when_constructed_then_debugLogFn_is_the_supplied_loggers_log_function(
            self, a_session, mock_logger):

        # pylint: disable=protected-access
        assert a_session._debugLogFn is mock_logger.log

    def test_when_constructed_with_null_host_interface_then_ValueError_is_raised(
            self, mock_logger, mock_manager_factory):

        with pytest.raises(ValueError):
            Session(None, mock_logger, mock_manager_factory)

    def test_when_constructed_with_invalid_host_interface_type_then_ValueError_is_raised(
            self, mock_logger, mock_manager_factory):

        with pytest.raises(ValueError):
            Session(mock_logger, mock_logger, mock_manager_factory)


class Test_Session_registeredManagers:

    def test_wraps_the_supplied_factory_method(
            self, a_session, mock_manager_factory):

        mock_manager_factory.managers.assert_not_called()
        assert a_session.registeredManagers() == mock_manager_factory.managers.return_value
        mock_manager_factory.managers.assert_called_once_with()


class Test_Session_useManager:

    def test_when_called_with_a_valid_identifier_then_it_is_not_immediately_instantiated(
            self, a_session, mock_manager_factory):

        # Not testing lifetime management of manager instances here in too much detail
        # As this isn't set in stone, and will change with the `cpp` implementation.

        mock_manager_factory.managerRegistered.return_value = True

        an_id = "com.manager"
        a_session.useManager(an_id)
        mock_manager_factory.managerRegistered.assert_called_once_with(an_id)
        mock_manager_factory.instantiate.assert_not_called()

    def test_when_called_with_an_invalid_identifier_then_a_ManagerException_is_raised(
            self, a_session, mock_manager_factory):

        mock_manager_factory.managerRegistered.return_value = False

        an_id = "com.manager"
        with pytest.raises(exceptions.ManagerException):
            a_session.useManager(an_id)
        mock_manager_factory.managerRegistered.assert_called_once_with(an_id)
        mock_manager_factory.instantiate.assert_not_called()


class Test_Session_currentManager:
    # pylint: disable=protected-access

    def test_when_useManager_has_not_been_called_then_factory_is_not_queried(
            self, a_session, mock_manager_factory):

        # Not testing lifetime management of manager instances here in too much detail
        # As this isn't set in stone, and will change with the `cpp` implementation.

        assert a_session.currentManager() is None
        mock_manager_factory.assert_not_called()

    def test_when_useManager_was_called_with_valid_identifier_then_initializes_expected_manager(
            self, a_session, mock_manager_interface, mock_manager_factory, mock_host_interface):

        an_id = "com.manager"
        a_session.useManager(an_id)

        manager = a_session.currentManager()

        assert isinstance(manager, Manager)
        assert manager._interface() is mock_manager_interface
        assert manager._debugLogFn is a_session._debugLogFn
        mock_manager_factory.instantiate.assert_called_once_with(an_id)
        mock_manager_interface.mock.initialize.assert_called_once()
        mock_manager_interface.mock.setSettings.assert_not_called()
        # Assert provided host session contains the expected host. We
        # assume correct behaviour of Host methods, i.e. that they
        # delegate to the HostInterface as appropriate.
        # I.e. we set HostInterface.identifier() to some known value,
        # then check that the host returned by the HostSession, captured
        # by our StubManager during initialization (above) returns this
        # same value.
        expected_identifier = "some.identifier"
        mock_host_interface.identifier.return_value = expected_identifier
        host_session = mock_manager_interface.mock.initialize.call_args[0][0]
        assert host_session.host().identifier() == expected_identifier

    def test_when_repeatedly_called_then_the_manager_is_only_initialized_once(
            self, a_session, mock_manager_interface, mock_manager_factory):

        an_id = "com.manager"
        a_session.useManager(an_id)

        manager = a_session.currentManager()

        assert isinstance(manager, Manager)
        assert manager._interface() is mock_manager_interface
        assert manager._debugLogFn is a_session._debugLogFn
        mock_manager_factory.instantiate.assert_called_once_with(an_id)
        mock_manager_interface.mock.initialize.assert_called_once()
        mock_manager_interface.mock.setSettings.assert_not_called()
        mock_manager_factory.reset_mock()

        assert a_session.currentManager() is manager
        mock_manager_factory.instantiate.assert_not_called()

    def test_when_useManager_called_with_another_id_then_the_new_manager_is_initialized(
            self, a_session, mock_manager_interface, mock_manager_factory):

        an_id = "com.manager"
        a_session.useManager(an_id)
        manager = a_session.currentManager()
        mock_manager_factory.instantiate.assert_called_once_with(an_id)
        mock_manager_interface.mock.initialize.assert_called_once()
        mock_manager_factory.reset_mock()
        mock_manager_interface.mock.reset_mock()

        another_id = "com.manager.b"
        a_session.useManager(another_id)
        mock_manager_factory.instantiate.assert_not_called()
        manager_b = a_session.currentManager()
        assert manager_b is not manager
        assert manager_b._interface() is mock_manager_interface
        assert manager_b._debugLogFn is a_session._debugLogFn
        mock_manager_factory.instantiate.assert_called_once_with(another_id)
        mock_manager_interface.mock.initialize.assert_called_once()

    def test_when_useManager_called_with_settings_then_new_manager_initialized_with_settings(
            self, a_session, mock_manager_interface, mock_manager_factory):

        an_id = "com.manager"
        some_settings = {"k": "v"}
        a_session.useManager(an_id, settings=some_settings)

        mock_manager_factory.instantiate.assert_not_called()
        mock_manager_interface.mock.setSettings.assert_not_called()

        _ = a_session.currentManager()

        mock_manager_factory.instantiate.assert_called_once_with(an_id)
        mock_manager_interface.mock.initialize.assert_called_once()
        mock_manager_interface.mock.setSettings.assert_called_once()
        assert mock_manager_interface.mock.setSettings.call_args[0][0] == some_settings


class Test_Session_createContext:

    def test_when_called_with_no_current_manager_then_a_RuntimeError_is_raised(
            self, a_session, mock_manager_interface):

        with pytest.raises(RuntimeError):
            _ = a_session.createContext()

        mock_manager_interface.mock.createState.assert_not_called()

    def test_when_called_with_a_current_manager_then_context_is_created_with_expected_properties(
            self, a_session, mock_manager_interface):

        a_session.useManager("com.manager")

        state_a = "state-a"
        mock_manager_interface.mock.createState.return_value = state_a

        context_a = a_session.createContext()

        assert context_a.access == Context.kRead
        assert context_a.retention == Context.kTransient
        assert context_a.managerInterfaceState is state_a
        assert context_a.locale is None
        mock_manager_interface.mock.createState.assert_called_once()

    def test_when_called_with_parent_then_props_copied_and_createState_called_with_parent_state(
            self, a_session, mock_manager_interface):
        # pylint: disable=protected-access

        a_session.useManager("com.manager")

        state_a = "state-a"
        mock_manager_interface.mock.createState.return_value = state_a
        context_a = a_session.createContext()
        context_a.access = Context.kWrite
        context_a.retention = Context.kSession
        context_a.locale = TraitsData()
        mock_manager_interface.mock.reset_mock()

        state_b = "state-b"
        mock_manager_interface.mock.createState.return_value = state_b
        a_host_session = a_session.currentManager()._Manager__hostSession

        context_b = a_session.createContext(parent=context_a)

        assert context_b is not context_a
        assert context_b.managerInterfaceState is state_b
        assert context_b.access == context_a.access
        assert context_b.retention == context_a.retention
        assert context_b.locale == context_b.locale
        mock_manager_interface.mock.createState.assert_called_once_with(
            a_host_session, parentState=state_a)


class Test_Session_freezeContext:

    def test_when_called_with_no_manager_then_RuntimeError_is_raised(self, a_session):

        with pytest.raises(RuntimeError):
            a_session.freezeContext(Context())

    def test_when_called_then_the_managers_frozen_token_is_returned(
             self, a_session, mock_manager_interface):

        expected_token = "a_frozen_token"
        mock_manager_interface.mock.freezeState.return_value = expected_token

        a_session.useManager("com.manager")

        initial_state = "initial_state"
        a_context = Context()
        a_context.managerInterfaceState = initial_state

        actual_token = a_session.freezeContext(a_context)

        assert actual_token == expected_token

        # pylint: disable=protected-access
        a_host_session = a_session.currentManager()._Manager__hostSession
        mock_manager_interface.mock.freezeState.assert_called_once_with(
            initial_state, a_host_session)


class Test_Session_thawContext:

    def test_when_called_with_no_manager_then_RuntimeError_is_raised(self, a_session):

        with pytest.raises(RuntimeError):
            a_session.thawContext(Context())

    def test_when_called_then_the_managers_thawed_state_is_set_in_the_context(
             self, a_session, mock_manager_interface):

        expected_state = "thawed_state"
        mock_manager_interface.mock.thawState.return_value = expected_state

        a_session.useManager("com.manager")

        a_token = "frozen_token"
        a_context = a_session.thawContext(a_token)

        assert a_context.managerInterfaceState is expected_state

        # pylint: disable=protected-access
        a_host_session = a_session.currentManager()._Manager__hostSession
        mock_manager_interface.mock.thawState.assert_called_once_with(a_token, a_host_session)


class Test_Session_getSettings:

    def test_when_called_with_no_manager_then_identifier_key_is_empty(self, a_session):

        settings = a_session.getSettings()
        assert settings == {constants.kSetting_ManagerIdentifier: None}

    def test_when_called_with_a_manager_then_contains_manager_settings_and_identifier(
            self, a_session, mock_manager_interface):

        an_id = "com.manager"
        some_manager_settings = {"k": "v"}
        mock_manager_interface.mock.getSettings.return_value = some_manager_settings
        expected_settings = dict(some_manager_settings)
        expected_settings.update({constants.kSetting_ManagerIdentifier: an_id})

        a_session.useManager(an_id)

        assert a_session.getSettings() == expected_settings
        mock_manager_interface.mock.getSettings.assert_called_once()


class Test_Session_setSettings:

    def test_when_called_on_new_session_then_manger_and_settings_are_configured(
            self, a_session, mock_manager_interface, mock_manager_factory):

        an_id = "com.manager"
        manager_settings = {"k": "v"}
        some_settings = {constants.kSetting_ManagerIdentifier: an_id}
        some_settings.update(manager_settings)

        a_session.setSettings(some_settings)

        mock_manager_factory.instantiate.assert_not_called()
        mock_manager_interface.mock.setSettings.assert_not_called()

        _ = a_session.currentManager()

        mock_manager_factory.instantiate.assert_called_once_with(an_id)
        mock_manager_interface.mock.setSettings.assert_called_once()
        assert mock_manager_interface.mock.setSettings.call_args[0][0] == manager_settings
