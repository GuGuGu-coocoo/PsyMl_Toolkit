extends RefCounted
## Shared table rendering for analysis data, prediction data and prediction output.

static func variables(tree: Tree, columns: Array) -> void:
	tree.clear()
	tree.columns = 3
	tree.hide_root = true
	tree.column_titles_visible = true
	for index in range(3):
		tree.set_column_title(index, TranslationServer.translate(["COLUMN", "TYPE", "MISSING_COUNT"][index]))
	var root := tree.create_item()
	for column in columns:
		var row := tree.create_item(root)
		row.set_text(0, str(column.name))
		row.set_text(1, str(column.dtype))
		row.set_text(2, str(int(column.missing_count)))


static func sample(tree: Tree, rows: Array, columns: Array = []) -> void:
	tree.clear()
	tree.column_titles_visible = not rows.is_empty()
	if rows.is_empty():
		return
	var headers: Array = []
	for column in columns:
		headers.append(column.name)
	if headers.is_empty():
		headers = rows[0].keys()
	tree.columns = headers.size()
	tree.hide_root = true
	tree.column_titles_visible = true
	for index in range(headers.size()):
		tree.set_column_title(index, str(headers[index]))
		tree.set_column_custom_minimum_width(index, 150)
		tree.set_column_expand(index, false)
	var root := tree.create_item()
	for values in rows:
		var item := tree.create_item(root)
		for index in range(headers.size()):
			item.set_text(index, str(values.get(headers[index], "")))
			item.set_text_overrun_behavior(index, TextServer.OVERRUN_TRIM_ELLIPSIS)
			item.set_tooltip_text(index, str(values.get(headers[index], "")))
