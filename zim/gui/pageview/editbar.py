# Copyright 2020, 2021 Jaap Karssenberg <jaap.karssenberg@gmail.com>

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Gio

from zim.plugins import PluginManager, list_actions


class EditActionMixin(object):
	'''Base class for EditBar and ToolBar implementations that want to include
	formatting actions
	'''

	def __init__(self, pageview):
		self.pageview = pageview
		self.edit_format_actions = (
			pageview.toggle_format_strong,
			pageview.toggle_format_emphasis,
			pageview.toggle_format_mark,
			pageview.toggle_format_strike,
			pageview.toggle_format_code,
			pageview.toggle_format_sub,
			pageview.toggle_format_sup,
		)
		self.edit_menus = (
			('_Format', 'document-edit-symbolic', self._create_format_menu()),
			('_Insert', 'insert-image-symbolic', self._create_insert_menu()),
		)
		self.edit_clear_action = pageview.clear_formatting

		def on_extensions_changed(o, obj):
			if obj in (pageview, PluginManager.insertedobjects):
				self._update_insert_menu()

		PluginManager.connect('extensions-changed', on_extensions_changed)

	def _create_format_menu(self):
		menu = Gio.Menu()
		section = Gio.Menu()
		menu.append_section(None, section)

		pageview = self.pageview
		for action in (
			pageview.apply_format_h1,
			pageview.apply_format_h2,
			pageview.apply_format_h3,
			pageview.apply_format_h4,
			pageview.apply_format_h5,
			'----',
			pageview.apply_format_bullet_list,
			pageview.apply_format_numbered_list,
			pageview.apply_format_checkbox_list,
		):
			if action == '----':
				section = Gio.Menu()
				menu.append_section(None, section)
			else:
				section.append(action.label, 'pageview.' + action.name)

		return menu

	def _create_insert_menu(self):
		menu = Gio.Menu()
		self._insert_menu = menu
		return menu

	def _update_insert_menu(self):
		menu = self._insert_menu
		menu.remove_all()

		section = Gio.Menu()
		menu.append_section(None, section)

		plugin_section = None
		seen = set((
			'insert_bullet_list',
			'insert_numbered_list',
			'insert_checkbox_list',
		)) # Ignore these 3 even if they have "insert" menuhint
		pageview = self.pageview
		for action in (
			pageview.attach_file,
			'----',
			pageview.show_insert_image,
			pageview.insert_text_from_file,
			'----',
			'<plugins>',
			'----',
			pageview.insert_date,
			pageview.insert_line,
			pageview.insert_link,
		):
			if action == '----':
				section = Gio.Menu()
				menu.append_section(None, section)
			elif action == '<plugins>':
				plugin_section = section
			else:
				section.append(action.label, 'pageview.' + action.name)
				seen.add(action.name)

		for name, action in list_actions(pageview):
			if action.menuhints[0] == 'insert' and not action.name in seen:
				plugin_section.append(action.label, 'pageview.' + action.name)
				seen.add(action.name)


class EditBar(EditActionMixin, Gtk.ActionBar):

	def __init__(self, pageview):
		Gtk.ActionBar.__init__(self)
		EditActionMixin.__init__(self, pageview)

		def _grab_focus_on_click(button):
			# Need additional check for has_focus, else this grab will happen
			# for every state change of the underlying action
			if button.has_focus():
				pageview.grab_focus()

		for action in self.edit_format_actions:
			button = action.create_icon_button()
			button.connect('clicked', _grab_focus_on_click)
			self.pack_start(button)

		for label, icon_name, menu in self.edit_menus:
			button = self._create_menu_button(label, icon_name, menu)
			self.pack_start(button)

		clear_button = self.edit_clear_action.create_icon_button()
		clear_button.connect('clicked', lambda o: pageview.grab_focus())
		self.pack_end(clear_button)

		self.insert_state_label = Gtk.Label()
		self.insert_state_label.set_sensitive(False)
		self.pack_end(self.insert_state_label)
		textview = pageview.textview
		self.on_textview_toggle_overwrite(textview)
		textview.connect_after(
			'toggle-overwrite', self.on_textview_toggle_overwrite)

		self.style_info_label = Gtk.Label()
		self.style_info_label.set_sensitive(False)
		self.style_info_label.set_ellipsize(Pango.EllipsizeMode.END)
		self.pack_end(self.style_info_label)
		pageview.connect(
			'textstyle-changed', self.on_textview_textstyle_changed)

	def _create_menu_button(self, label, icon_name, menu):
		button = Gtk.MenuButton()
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
		hbox.add(Gtk.Label.new_with_mnemonic(label))
		hbox.add(Gtk.Image.new_from_icon_name('pan-down-symbolic', Gtk.IconSize.BUTTON))
		button.add(hbox)

		popover = Gtk.Popover()
		popover.bind_model(menu)
		popover.connect('closed', lambda o: self.pageview.grab_focus())
		button.set_popover(popover)

		return button

	def on_textview_toggle_overwrite(self, textview):
		text = 'OVR' if textview.get_overwrite() else 'INS'
		self.insert_state_label.set_text(text + '  ')

	def on_textview_textstyle_changed(self, pageview, styles):
		label = ", ".join([s.title() for s in styles if s]) if styles else ''
		self.style_info_label.set_text(label)
