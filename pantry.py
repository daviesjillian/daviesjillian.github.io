import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from recipe_api import get_recipes, get_recipe_details  # Import recipe functions
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Google Sheets Authentication
SHEET_ID = "1Ti8xsHgcgpmQY5fndEViV4d67nkCIQc0NRhqkf6tAUk"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def load_pantry():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def save_pantry(df):
    df["Expiration_Date"] = df["Expiration_Date"].astype(str)
    print("\n📤 Saving the following data to Google Sheets:\n")
    print(df.to_string(index=False))
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("✅ Data successfully saved to Google Sheets!")
    # sheet.clear()
    # sheet.update([df.columns.values.tolist()] + df.values.tolist())

def alert_expiring_items(days=3):
    df = load_pantry()
    today = pd.Timestamp.today()
    df["Expiration_Date"] = pd.to_datetime(df["Expiration_Date"], errors = "coerce")
    df = df.dropna(subset = ["Expiration_Date"])
    soon = df[df["Expiration_Date"] <= today + pd.Timedelta(days = days)]
    if not soon.empty:
        print("\n🚨 ALERT: The following items are expiring soon:")
        print(soon.to_string(index = False))
    else:
        print("\n✅ All pantry items are good for now.")

def add_item(item, expiration_date):
    from datetime import datetime
    while True:
        try:
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
            break
        except ValueError:
            print("❌ Invalid date format! Please use YYYY-MM-DD.")
            expiration_date = input("Expiration date (YYYY-MM-DD): ")
    df = load_pantry()
    if not df.empty:
        df["Expiration_Date"] = pd.to_datetime(df["Expiration_Date"], errors = "coerce").dt.date
    new_entry = pd.DataFrame({"Item": [item], "Expiration_Date": [expiration_date]})
    df = pd.concat([df, new_entry], ignore_index = True)
    # Sort by expiration date
    df = df.sort_values(by="Expiration_Date")
    save_pantry(df)
    print(f"✅ {item} added successfully!")

    # df = load_pantry()
    # new_entry = pd.DataFrame({"Item": [item], "Expiration_Date": [expiration_date]})
    # df = pd.concat([df, new_entry], ignore_index=True)
    # df = df.sort_values(by="Expiration_Date")
    # save_pantry(df)
    # print(f"✅ {item} added successfully!")

def display_pantry():
    df = load_pantry()
    print("\n📌 Pantry Items (Sorted by Expiration Date):\n")
    print(df.to_string(index=False))

def check_expiring_soon(days = 3):
    df = load_pantry()
    today = pd.Timestamp.today()
    df["Expiration_Date"] = pd.to_datetime(df["Expiration_Date"], errors = "coerce")
    df = df.dropna(subset=["Expiration_Date"])
    soon = df[df["Expiration_Date"] <= today + pd.Timedelta(days = days)]
    if soon.empty:
        print("\n✅ No items expiring soon.")
    else:
        print("\n⚠️ Items Expiring Soon:\n", soon.to_string(index = False))
    # soon = df[df["Expiration_Date"] <= today + pd.Timedelta(days=days)]
    # print("\n⚠️ Items Expiring Soon:\n", soon.to_string(index=False))

def suggest_recipes():
    df = load_pantry()
    ingredients = df["Item"].tolist()
    if not ingredients:
        print("\n❌ No ingredients found in pantry!")
        return
    diet = input("Enter a diet preference (e.g., vegetarian, keto) or press Enter to skip: ")
    intolerance_input = input("Enter any intolerances separated by commas (e.g., gluten,dairy) or press Enter to skip: ")
    intolerances = ",".join(i.strip() for i in intolerance_input.split(",")) if intolerance_input else None
    print("\n🔍 Searching for recipes...")
    recipes = get_recipes(ingredients, diet = diet or None, intolerances = intolerances)
    if isinstance(recipes, str):
        print(recipes)
        return
    if not recipes:
        print("❌ No recipes found with the given filters.")
        return
    print("\n🍽️ Suggested Recipes:")
    for i, recipe in enumerate(recipes):
        print(f"{i+1}. {recipe['title']} (ID: {recipe['id']})")
    choice = input("\nEnter recipe number for details (or press Enter to skip): ")
    if choice.isdigit() and 1 <= int(choice) <= len(recipes):
        recipe_id = recipes[int(choice) - 1]['id']
        recipe_details = get_recipe_details(recipe_id)
        if isinstance(recipe_details, str):
            print(recipe_details)
            return
        print("\n📖 Recipe Details:")
        print("Title:", recipe_details["title"])
        print("Ingredients:", [i["original"] for i in recipe_details["extendedIngredients"]])
        print("Instructions:", recipe_details["instructions"])

def send_expiration_alerts(email_address):
    load_dotenv()
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("❌ EMAIL_ADDRESS or EMAIL_PASSWORD not set in environment variables.")
        return
    df = load_pantry()
    df["Expiration_Date"] = pd.to_datetime(df["Expiration_Date"], errors="coerce")
    df = df.dropna(subset=["Expiration_Date"])
    today = pd.Timestamp.today()
    soon = df[df["Expiration_Date"] <= today + pd.Timedelta(days=3)]
    if soon.empty:
        print("✅ No items expiring soon. No email sent.")
        return
    msg = EmailMessage()
    msg["Subject"] = "⏰ Pantry Expiration Alert"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email_address
    body = "Hey! 👋\n\n 🚨These pantry items are expiring soon:\n\n"
    for _, row in soon.iterrows():
        item = row['Item']
        exp_date = row['Expiration_Date'].date()
        body += f"• {item} (Expires: {exp_date})\n"
    body += "\nMake sure to use them up or toss what’s bad! 🥦🥫"
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("📧 Expiration alert email sent successfully!")
    except Exception as e:
        print("❌ Failed to send email:", e)
    # df = load_pantry()
    # df["Expiration_Date"] = pd.to_datetime(df["Expiration_Date"], errors = "coerce")
    # df = df.dropna(subset = ["Expiration_Date"])
    # today = pd.Timestamp.today()
    # soon = df[df["Expiration_Date"] <= today + pd.Timedelta(days = 3)]
    # if soon.empty:
    #     print("No items expiring soon. No email sent.")
    #     return
    # sender_email = os.getenv("EMAIL_ADDRESS")
    # sender_password = os.getenv("EMAIL_PASSWORD")
    # msg = EmailMessage()
    # msg["Subject"] = "⏰ Pantry Expiration Alert"
    # msg["From"] = sender_email
    # msg["To"] = email_address
    # body = "The following items are expiring soon:\n\n"
    # for _, row in soon.iterrows():
    #     body += f" - {row['Item']} (Expires: {row['Expiration_Date'].date()}\n"
    # msg.set_content(body)
    # try:
    #     with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    #         smtp.login(sender_email, sender_password)
    #         smtp.send_message(msg)
    #     print("📧 Expiration alert email sent successfully!")
    # except Exception as e:
    #     print("❌ Failed to send email:", e)

def main():
    while True:
        print("\n📦 Smart Pantry Tracker")
        print("1️⃣ Add Food Item")
        print("2️⃣ View Pantry")
        print("3️⃣ Check Expiring Soon")
        print("4️⃣ Find Recipes")
        print("5️⃣ Send Expiration Email Alert")
        print("6️⃣ Exit")
        choice = input("Enter choice: ")
        if choice == "1":
            item = input("Item name: ")
            expiration = input("Expiration date (YYYY-MM-DD): ")
            try:
                datetime.strptime(expiration, "%Y-%m-%d")
                add_item(item, expiration)
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD.")
        elif choice == "2":
            display_pantry()
        elif choice == "3":
            check_expiring_soon()
        elif choice == "4":
            suggest_recipes()
        elif choice == "5":
            email = input("Enter email address to send alert to: ")
            send_expiration_alerts(email)
        elif choice == "6":
            break

if __name__ == "__main__":
    main()

