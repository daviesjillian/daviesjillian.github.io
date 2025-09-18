import requests

API_KEY = "ff177f518c0b42c485ebca265510dcba"
BASE_URL = "https://api.spoonacular.com/recipes/findByIngredients"

def get_recipes(ingredients, diet = None, intolerances = None, number = 5):
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "apiKey": API_KEY,
        "ingredients": ",".join(ingredients),
        "number": number * 2,
        "ranking": 1,
        "ignorePantry": True
    }
    try:
        response = requests.get(url, params = params)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return f"API Error: {e}"
    if not diet and not intolerances:
        return data[:number]
    filtered = []
    for recipe in data:
        recipe_id = recipe["id"]
        details = get_recipe_details(recipe_id)
        if isinstance(details, str):
            continue
        matches_diet = (not diet or details.get("diets") and diet.lower() in [d.lower() for d in details["diets"]])
        avoids_intolerances = True
        if intolerances:
            intolerances_list = [i.strip().lower() for i in intolerances.split(",")]
            ingredient_names = [i["name"].lower() for i in details.get("extendedIngredients", [])]
            avoids_intolerances = all(i not in ingredient_names for i in intolerances_list)
        if matches_diet and avoids_intolerances:
            filtered.append(details)
        if len(filtered) >= number:
            break
    return filtered

def get_recipe_details(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {"apiKey": API_KEY}
    try:
        response = requests.get(url, params = params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return f"Error fetching recipe {recipe_id}: {e}"
