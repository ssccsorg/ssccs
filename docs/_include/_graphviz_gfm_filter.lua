function CodeBlock(el)
  if el.classes:includes("python") then
    local content = el.text
    local dot_content = content:match('dot%s*%(%s*"""%s*(.-)%s*"""%s*%)')
    if dot_content then
      dot_content = dot_content:gsub("^%s*\n", ""):gsub("\n%s*$", "")
      local new_block = pandoc.CodeBlock(dot_content, {class="dot", lang="dot"})
      new_block.attributes = {}
      return new_block
    end
  end
  return el
end