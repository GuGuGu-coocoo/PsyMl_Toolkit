class_name ScrollGestureRouter
extends Node
## Routes wheel and touchpad pan gestures to one scroll layer per gesture.
##
## The first scroll event picks the innermost visible scrollable control under
## the pointer and locks it as the gesture owner. Every later event of the same
## gesture is delivered to that owner even when the pointer crosses a nested
## table, so a gesture that started on the page keeps scrolling the page and a
## gesture that started on a table keeps scrolling the table.
##
## The lock only ever affects wheel and pan events: non-owner scrollers are made
## transparent to pointer input for the single re-dispatch instant and restored
## before the GUI phase handles anything, so clicks, selection, dragging and
## hover are never weakened or swallowed. The owner is pinned to
## `mouse_force_pass_scroll_events = false` for the same instant so it never
## chains past its own boundary. Native speed and horizontal/vertical handling
## are preserved: the event is re-dispatched unchanged except for its position,
## and a re-entrancy guard prevents duplicate delivery.
##
## The lock is released after RELEASE_DELAY_MSEC without a scroll event, when
## the owner is hidden or freed, when the window loses focus, or when the
## caller reports a page change.

## Milliseconds without a scroll event after which the gesture owner is freed.
## Kept as a named constant so it can be tuned by hand after device testing.
const RELEASE_DELAY_MSEC := 250

var gesture_owner: Control = null
## Overridable release delay; tests may shorten it, production keeps the constant.
var release_delay_msec := RELEASE_DELAY_MSEC

var _deadline_msec := 0
var _forwarding := false
var _neutralized: Array[Dictionary] = []


func _ready() -> void:
	set_process(false)


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		release()


## Drops the current lock and restores every control touched while it was held.
func release() -> void:
	_restore()
	gesture_owner = null
	set_process(false)


func is_scroll_event(event: InputEvent) -> bool:
	if event is InputEventMouseButton:
		return event.button_index in [
			MOUSE_BUTTON_WHEEL_UP,
			MOUSE_BUTTON_WHEEL_DOWN,
			MOUSE_BUTTON_WHEEL_LEFT,
			MOUSE_BUTTON_WHEEL_RIGHT,
		]
	return event is InputEventPanGesture


func is_scrollable(control: Node) -> bool:
	if control is ScrollContainer or control is Tree or control is ItemList or control is TextEdit:
		return true
	return control is RichTextLabel and control.scroll_active


## Innermost visible scrollable control under `point`, or null when the point is
## over no scroll layer. Clipping ancestors are honored so a table scrolled out
## of view is never chosen.
func find_scrollable_at(point: Vector2) -> Control:
	var found: Control = null
	var root_node := _search_root()
	if root_node == null:
		return null
	for node in root_node.find_children("*", "Control", true, false):
		var control: Control = node
		if not is_scrollable(control) or not control.is_visible_in_tree():
			continue
		if not control.get_global_rect().has_point(point):
			continue
		if not _is_reachable(control, point):
			continue
		if found == null or found.is_ancestor_of(control):
			found = control
	return found


func _input(event: InputEvent) -> void:
	if _forwarding or not is_inside_tree() or not is_scroll_event(event):
		# Only wheel/pan events enter the routing path. Clicks, selection,
		# dragging and hover keep their native behavior untouched.
		return
	if gesture_owner != null and not _owner_valid():
		release()
	if gesture_owner == null:
		gesture_owner = find_scrollable_at(event.position)
		if gesture_owner == null:
			return
	_lock()
	_forward(event)


func _process(_delta: float) -> void:
	if gesture_owner == null:
		set_process(false)
		return
	if not _owner_valid() or Time.get_ticks_msec() >= _deadline_msec:
		release()


func _lock() -> void:
	_deadline_msec = Time.get_ticks_msec() + release_delay_msec
	set_process(true)


func _owner_valid() -> bool:
	return is_instance_valid(gesture_owner) and gesture_owner.is_visible_in_tree()


func _forward(event: InputEvent) -> void:
	# Re-dispatch a copy positioned inside the owner so the owner (and only the
	# owner) handles it with its native speed. Non-owner scrollers are filtered
	# only for this dispatch and restored right after, before the GUI phase
	# handles any pointer event, so they cannot steal the gesture and no click,
	# hover or drag state is affected. The original event is consumed so
	# nothing else reacts twice.
	var clone := event.duplicate()
	var rect := gesture_owner.get_global_rect()
	var margin := Vector2(minf(8.0, rect.size.x / 4.0), minf(8.0, rect.size.y / 4.0))
	var point: Vector2 = event.position.clamp(rect.position + margin, rect.end - margin)
	clone.position = point
	if clone is InputEventMouse:
		clone.global_position = point
	_neutralize()
	_forwarding = true
	get_viewport().push_input(clone, true)
	_forwarding = false
	_restore()
	get_viewport().set_input_as_handled()


func _neutralize() -> void:
	_neutralized.clear()
	var root_node := _search_root()
	if root_node == null:
		return
	for node in root_node.find_children("*", "Control", true, false):
		var control: Control = node
		if not is_scrollable(control) or control == gesture_owner:
			continue
		_remember_filter(control)
		for child in control.get_children():
			if child is ScrollBar:
				_remember_filter(child)
	_neutralized.append(
		{"node": gesture_owner, "filter": null, "pass": gesture_owner.mouse_force_pass_scroll_events}
	)
	gesture_owner.mouse_force_pass_scroll_events = false


func _remember_filter(control: Control) -> void:
	_neutralized.append({"node": control, "filter": control.mouse_filter, "pass": null})
	control.mouse_filter = Control.MOUSE_FILTER_IGNORE


func _restore() -> void:
	for entry in _neutralized:
		var control: Control = entry["node"]
		if not is_instance_valid(control):
			continue
		# Restore only the values this router set; a handler that changed one
		# during the re-dispatch keeps its newer value.
		if entry["filter"] != null and control.mouse_filter == Control.MOUSE_FILTER_IGNORE:
			control.mouse_filter = entry["filter"]
		if entry["pass"] != null and not control.mouse_force_pass_scroll_events:
			control.mouse_force_pass_scroll_events = entry["pass"]
	_neutralized.clear()


func _search_root() -> Node:
	# Search only the UI subtree this router lives in, so hidden popups and
	# other windows can never become the owner.
	return get_parent()


func _is_reachable(control: Control, point: Vector2) -> bool:
	var ancestor: Node = control
	while ancestor is Control:
		if ancestor.clip_contents and not ancestor.get_global_rect().has_point(point):
			return false
		ancestor = ancestor.get_parent()
	return true
