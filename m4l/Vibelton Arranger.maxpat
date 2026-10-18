{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 8,
			"minor": 6,
			"revision": 0,
			"architecture": "x64",
			"modernui": 1
		},
		"classnamespace": "box",
		"rect": [
			100.0,
			100.0,
			800.0,
			500.0
		],
		"bglocked": 0,
		"openinpresentation": 1,
		"default_fontsize": 11.0,
		"default_fontface": 0,
		"default_fontname": "Ableton Sans Medium",
		"gridonopen": 1,
		"gridsize": [
			10.0,
			10.0
		],
		"gridsnaponopen": 1,
		"objectsnaponopen": 1,
		"statusbarvisible": 2,
		"toolbarvisible": 1,
		"lefttoolbarpinned": 0,
		"toptoolbarpinned": 0,
		"righttoolbarpinned": 0,
		"bottomtoolbarpinned": 0,
		"toolbars_unpinned_last_save": 0,
		"tallnewobj": 0,
		"boxanimatetime": 200,
		"enablehscroll": 0,
		"enablevscroll": 0,
		"devicewidth": 750.0,
		"description": "Vibelton Arranger: In-DAW Subtractive Arrangement Companion for Ableton Live 12",
		"digest": "Subtractive arrangement engine and stem loop organizer",
		"tags": "vibelton arranger arrangement maxforlive",
		"style": "",
		"subpatcher_template": "",
		"assistshowspatchername": 0,
		"boxes": [
			{
				"box": {
					"id": "obj-1",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"signal"
					],
					"patching_rect": [
						30.0,
						30.0,
						38.0,
						22.0
					],
					"text": "in~ 1"
				}
			},
			{
				"box": {
					"id": "obj-2",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						30.0,
						70.0,
						44.0,
						22.0
					],
					"text": "out~ 1"
				}
			},
			{
				"box": {
					"id": "obj-3",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"signal"
					],
					"patching_rect": [
						90.0,
						30.0,
						38.0,
						22.0
					],
					"text": "in~ 2"
				}
			},
			{
				"box": {
					"id": "obj-4",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						90.0,
						70.0,
						44.0,
						22.0
					],
					"text": "out~ 2"
				}
			},
			{
				"box": {
					"annotation": "Vibelton Arranger: Subtractive arrangement engine and stem organizer for Ableton Live 12. Duplicates your 8-bar or 16-bar loops subtractively across the timeline into full club structures with 1-click panic rollback.",
					"hint": "Vibelton Arranger Companion",
					"id": "obj-5",
					"maxclass": "live.thisdevice",
					"numinlets": 1,
					"numoutlets": 3,
					"outlettype": [
						"bang",
						"int",
						"int"
					],
					"patching_rect": [
						160.0,
						30.0,
						100.0,
						22.0
					],
					"varname": "VibeltonArranger"
				}
			},
			{
				"box": {
					"id": "obj-6",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					],
					"patching_rect": [
						280.0,
						30.0,
						56.0,
						22.0
					],
					"text": "loadbang"
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						280.0,
						70.0,
						68.0,
						22.0
					],
					"text": "script start"
				}
			},
			{
				"box": {
					"id": "obj-8",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					],
					"patching_rect": [
						280.0,
						110.0,
						170.0,
						22.0
					],
					"saved_object_attributes": {
						"autostart": 1,
						"defer": 0,
						"node": "",
						"npm": "",
						"watch": 0
					},
					"text": "node.script daemon_guard.js"
				}
			},
			{
				"box": {
					"id": "obj-9",
					"maxclass": "newobj",
					"numinlets": 3,
					"numoutlets": 6,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						""
					],
					"patching_rect": [
						280.0,
						150.0,
						330.0,
						22.0
					],
					"text": "route status open_popout offline_url server_url retry"
				}
			},
			{
				"box": {
					"id": "obj-10",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						355.0,
						190.0,
						50.0,
						22.0
					],
					"text": "popout"
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 0,
					"patcher": {
						"fileversion": 1,
						"appversion": {
							"major": 8,
							"minor": 6,
							"revision": 0,
							"architecture": "x64",
							"modernui": 1
						},
						"classnamespace": "box",
						"rect": [
							150.0,
							150.0,
							1050.0,
							700.0
						],
						"bglocked": 0,
						"openinpresentation": 0,
						"default_fontsize": 11.0,
						"default_fontface": 0,
						"default_fontname": "Ableton Sans Medium",
						"gridonopen": 1,
						"gridsize": [
							10.0,
							10.0
						],
						"toolbarvisible": 0,
						"visible": 0,
						"bgcolor": [
							0.118,
							0.118,
							0.118,
							1.0
						],
						"editing_bgcolor": [
							0.118,
							0.118,
							0.118,
							1.0
						],
						"boxes": [
							{
								"box": {
									"comment": "Input trigger to open or control popout",
									"id": "obj-p1",
									"index": 1,
									"maxclass": "inlet",
									"numinlets": 0,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										20.0,
										20.0,
										30.0,
										30.0
									]
								}
							},
							{
								"box": {
									"id": "obj-p2",
									"maxclass": "jweb",
									"numinlets": 1,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										0.0,
										0.0,
										900.0,
										550.0
									],
									"rendermode": 2,
									"url": "http://127.0.0.1:8765/arranger_device.html?popout=1",
									"varname": "popout_jweb"
								}
							},
							{
								"box": {
									"id": "obj-p3",
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										20.0,
										60.0,
										75.0,
										22.0
									],
									"text": "window flags float, window exec, wvis 1, front"
								}
							},
							{
								"box": {
									"id": "obj-p4",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 2,
									"outlettype": [
										"",
										""
									],
									"patching_rect": [
										20.0,
										95.0,
										68.0,
										22.0
									],
									"text": "thispatcher"
								}
							},
							{
								"box": {
									"id": "obj-p5",
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"patching_rect": [
										105.0,
										95.0,
										95.0,
										22.0
									],
									"text": "js autoresize.js"
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"destination": [
										"obj-p3",
										0
									],
									"source": [
										"obj-p1",
										0
									]
								}
							},
							{
								"patchline": {
									"destination": [
										"obj-p5",
										0
									],
									"source": [
										"obj-p1",
										0
									]
								}
							},
							{
								"patchline": {
									"destination": [
										"obj-p4",
										0
									],
									"source": [
										"obj-p3",
										0
									]
								}
							}
						]
					},
					"patching_rect": [
						355.0,
						230.0,
						80.0,
						22.0
					],
					"saved_object_attributes": {
						"default_fontface": 0,
						"default_fontname": "Ableton Sans Medium",
						"default_fontsize": 11.0,
						"description": "",
						"digest": "",
						"floating": 1,
						"fontname": "Ableton Sans Medium",
						"fontsize": 11.0,
						"globalpatchername": "",
						"style": "",
						"tags": "",
						"title": "Vibelton Arranger \u00b7 Expanded Studio View"
					},
					"text": "p popout"
				}
			},
			{
				"box": {
					"annotation": "Vibelton Arranger: In-DAW Subtractive Clip Placement & Stem Organizer. Click Pop Out to expand into a floating studio view.",
					"hint": "Vibelton Arranger Web UI",
					"id": "obj-12",
					"maxclass": "jweb",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						30.0,
						280.0,
						750.0,
						190.0
					],
					"presentation": 1,
					"presentation_rect": [
						0.0,
						0.0,
						750.0,
						190.0
					],
					"rendermode": 2,
					"url": "http://127.0.0.1:8765/arranger_device.html",
					"enablemaxobject": 1
				}
			},
			{
				"box": {
					"id": "obj-14",
					"maxclass": "live.text",
					"mode": 0,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					],
					"parameter_enable": 1,
					"patching_rect": [
						450.0,
						150.0,
						80.0,
						20.0
					],
					"presentation": 1,
					"presentation_rect": [
						655.0,
						3.0,
						85.0,
						20.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_enum": [
								"val1",
								"val2"
							],
							"parameter_longname": "live.text[popout]",
							"parameter_mmax": 1,
							"parameter_modmode": 0,
							"parameter_shortname": "Popout",
							"parameter_type": 2
						}
					},
					"text": "\u2922 Pop Out",
					"texton": "\u2922 Pop Out",
					"varname": "live.text[popout]"
				}
			},
			{
				"box": {
					"id": "obj-15",
					"maxclass": "newobj",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						480.0,
						200.0,
						100.0,
						22.0
					],
					"text": "prepend loadurl"
				}
			},
			{
				"box": {
					"id": "obj-16",
					"maxclass": "message",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						590.0,
						200.0,
						50.0,
						22.0
					],
					"text": "retry"
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"destination": [
						"obj-2",
						0
					],
					"source": [
						"obj-1",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-4",
						0
					],
					"source": [
						"obj-3",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-7",
						0
					],
					"source": [
						"obj-5",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-7",
						0
					],
					"source": [
						"obj-6",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-8",
						0
					],
					"source": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-9",
						0
					],
					"source": [
						"obj-8",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-10",
						0
					],
					"source": [
						"obj-9",
						1
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-11",
						0
					],
					"source": [
						"obj-10",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-8",
						0
					],
					"source": [
						"obj-10",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-10",
						0
					],
					"source": [
						"obj-14",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-9",
						0
					],
					"source": [
						"obj-12",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-15",
						0
					],
					"source": [
						"obj-9",
						2
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-15",
						0
					],
					"source": [
						"obj-9",
						3
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-12",
						0
					],
					"source": [
						"obj-15",
						0
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-16",
						0
					],
					"source": [
						"obj-9",
						4
					]
				}
			},
			{
				"patchline": {
					"destination": [
						"obj-8",
						0
					],
					"source": [
						"obj-16",
						0
					]
				}
			}
		]
	}
}
