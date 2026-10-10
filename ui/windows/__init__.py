"""Main-window behavior split by interaction responsibility."""

from .startup import _MainWindowStartupMixin
from .settings import _MainWindowSettingsMixin
from .command_center import _MainWindowCommandMixin
from .layout_style import _MainWindowStyleMixin
from .layout_builders import _MainWindowLayoutMixin
from .interactions import _MainWindowInteractionMixin
from .onboarding import _MainWindowOnboardingMixin
from .identity import _MainWindowIdentityMixin

__all__ = ['_MainWindowStartupMixin', '_MainWindowSettingsMixin', '_MainWindowCommandMixin', '_MainWindowStyleMixin', '_MainWindowLayoutMixin', '_MainWindowInteractionMixin', '_MainWindowOnboardingMixin', '_MainWindowIdentityMixin']
