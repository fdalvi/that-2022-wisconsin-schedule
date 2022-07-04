import json
import re
import requests
import os

from argparse import ArgumentParser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_activities(schedule_url = 'https://that.us/events/wi/2022/schedule/'):
	html_text = requests.get(schedule_url).text
	soup = BeautifulSoup(html_text, 'html.parser')
	activity_set = set()
	for link in soup.find_all('a'):
		link_url = link.get('href')
		if link_url is None:
			continue
		match = re.search('/activities/([^/]+)/', link_url)
		if match and match.group(1) != "create":
			activity_set.add(link_url.strip())
	return activity_set

def main():
	parser = ArgumentParser()
	parser.add_argument("--no-cache", action="store_true")
	parser.add_argument("--check-new", action="store_true")
	args = parser.parse_args()

	cache = not args.no_cache

	if cache:
		os.makedirs(".cache", exist_ok=True)

	activity_set = set()
	if cache:
		if os.path.exists(".cache/activity_list.txt"):
			with open(".cache/activity_list.txt", "r") as fp:
				for activity in fp:
					activity_set.add(activity.strip())
	
	if args.check_new:
		latest_activities_set = get_activities()
		print(latest_activities_set - activity_set)
		return

	if len(activity_set) == 0:
		activity_set = get_activities()

	if cache:
		with open(".cache/activity_list.txt", "w") as fp:
			for activity in activity_set:
				fp.write(f"{activity}\n")

	all_activities = []
	for activity in activity_set:
		activity_id = re.search('/activities/([^/]+)/', activity).group(1)
		html_text = None
		if cache:
			if os.path.exists(f".cache/{activity_id}"):
				with open(f".cache/{activity_id}") as fp:
					html_text = fp.read()

		if html_text is None:
			activity_url = f'https://that.us/{activity}'
			print(f"Fetching {activity_url}")
			html_text = requests.get(activity_url).text

		if cache:
			with open(f".cache/{activity_id}", "w") as fp:
				fp.write(html_text)
		soup = BeautifulSoup(html_text, 'html.parser')

		title_element = soup.find("h2", class_="text-2xl")
		title = title_element.text

		date_element = title_element.next_sibling.next_sibling
		date = date_element.get_text().strip()
		try:
			lines = date.split("\n")
			if len(lines) == 7:
				date, duration, duration_2, _, _, _, _, = date.split("\n")
				location = "Online"
			elif len(lines) == 10:
				date, duration, duration_2, _, _, _, _, _, _, location = date.split("\n")
			else:
				raise Exception("unknown format!")
		except Exception as e:
			print("==============")
			print(date)
			print("==============")
			import sys
			sys.exit(1)

		# Wednesday, July 27, 2022 - 7:30 PM UTC
		start_time = datetime.strptime(date[:-5], '%A, %B %d, %Y - %I:%M %p %Z')
		assert "hour" in duration_2, f"{activity_id}: {duration} {duration_2}"
		end_time = start_time + timedelta(hours=float(duration))

		description_element = date_element.next_sibling.next_sibling.next_sibling.next_sibling
		description = description_element.get_text()

		activity_obj = {
			"title": title,
			"start_time": start_time.timestamp(),
			"end_time": end_time.timestamp(),
			"location": location,
			"description": description
		}
		all_activities.append(activity_obj)
		print(activity_obj["title"])
		with open(f".cache/{activity_id}.json", "w") as fp:
			json.dump(activity_obj, fp)

	with open(f"schedule.json", "w") as fp:
			json.dump(all_activities, fp)


if __name__ == '__main__':
	main()