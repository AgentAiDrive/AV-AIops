
import streamlit as st
from core.db.session import get_session
from core.db.models import Recipe
from core.recipes.service import list_recipe_files, load_recipe_dict, save_recipe_yaml
from core.recipes.validator import validate_yaml_text
import os

st.title("📜 Recipes")

RECIPES_DIR = os.path.join(os.getcwd(), "recipes")
os.makedirs(RECIPES_DIR, exist_ok=True)

files = list_recipe_files()
st.subheader("Create Recipe")
new_name = st.text_input("Recipe name")
new_file = st.text_input("Filename (e.g. my_recipe.yaml)")
new_text = st.text_area("YAML", height=220, value="name: Example\ndescription: Demo\nintake: []\nplan: []\nact: []\nverify: []")
if st.button("Save Recipe") and new_name and new_file:
    ok, msg = validate_yaml_text(new_text)
    if not ok:
        st.error(msg)
    else:
        save_recipe_yaml(new_file, new_text)
        with get_session() as db:  # type: ignore
            if not db.query(Recipe).filter(Recipe.name==new_name).first():
                db.add(Recipe(name=new_name, yaml_path=new_file)); db.commit()
        st.success("Recipe saved.")

st.divider()
st.subheader("Existing Recipes")
with get_session() as db:   # type: ignore
    recipes = db.query(Recipe).all()
    for r in recipes:
        with st.expander(r.name):
            path = os.path.join(RECIPES_DIR, r.yaml_path)
            text = open(path, "r", encoding="utf-8").read()
            edited = st.text_area(f"Edit {r.yaml_path}", value=text, height=200, key=f"e-{r.id}")
            if st.button("Update", key=f"u-{r.id}"):
                ok, msg = validate_yaml_text(edited)
                if ok:
                    save_recipe_yaml(r.yaml_path, edited); st.success("Updated.")
                else:
                    st.error(msg)
            if st.button("Delete", key=f"d-{r.id}"):
                try:
                    os.remove(path)
                except Exception:
                    pass
                db.delete(r); db.commit(); st.rerun()
