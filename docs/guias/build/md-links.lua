-- Links between guides point to their HTML version.
function Link(el)
  el.target = el.target:gsub("^([%w%-]+)%.md(#?.*)$", "%1.html%2")
  return el
end

-- The H1 becomes the page header (template), so it leaves the body.
function Header(el)
  if el.level == 1 then return {} end
  return el
end
