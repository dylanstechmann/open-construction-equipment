# SPDX-License-Identifier: Apache-2.0
"""Pure standard-library CAD and physics-interchange text generation.

No optional CAD or physics application is imported or executed here. Generated
geometry and scripts are synthetic visualization/simulation artifacts, not
manufacturing CAD, validated physics, or a fabrication release.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .config import ConfigError, _keys, _mapping, _number, load_json
from .physics import (
    EvidenceStatus,
    SyntheticProvenance,
    _at_least,
    _finite,
    _json_compatible,
    _parse_provenance,
    _product,
    _sum,
    _validate_provenance,
    bounded_fraction,
)

COORDINATE_CONVENTION_ID = "RIGHT_HANDED_LOCAL_METRES_Z_UP"
SYNTHETIC_NOTICE_ID = (
    "Synthetic AI-authored local geometry for visualization and simulation only; "
    "not surveyed, physically validated, fabrication-ready, or released."
)
ARTIFACT_FILENAMES = (
    "scene.obj",
    "scene.mtl",
    "blender_scene.py",
    "ctl01_bunker_physics.xml",
    "scene.scad",
    "scene_freecad.py",
)
_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*")


class CadBodyKind(StrEnum):
    MACHINE = "MACHINE"
    BUNKER = "BUNKER"
    ATTACHMENT = "ATTACHMENT"
    TERRAIN = "TERRAIN"
    MICROGRID = "MICROGRID"
    PRIVACY_BERM = "PRIVACY_BERM"


class PhysicsBodyMode(StrEnum):
    STATIC = "STATIC"
    RIGID = "RIGID"
    KINEMATIC = "KINEMATIC"


class AnimationInterpolation(StrEnum):
    LINEAR = "LINEAR"
    CONSTANT = "CONSTANT"


@dataclass(frozen=True)
class Vector3:
    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True)
class Color:
    red: float
    green: float
    blue: float
    alpha: float


@dataclass(frozen=True)
class MaterialSpec:
    material_id: str
    diffuse: Color
    metallic: float
    roughness: float


@dataclass(frozen=True)
class BoxBody:
    body_id: str
    kind: CadBodyKind
    center_m: Vector3
    size_m: Vector3
    yaw_rad: float
    mass_kg: float
    physics_mode: PhysicsBodyMode
    material_id: str


@dataclass(frozen=True)
class MeshObject:
    body: BoxBody
    vertices_m: tuple[Vector3, ...]
    triangles: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class AnimationKey:
    body_id: str
    time_s: float
    translation_m: Vector3
    yaw_rad: float
    interpolation: AnimationInterpolation


@dataclass(frozen=True)
class PhysicsSceneSpec:
    timestep_s: float
    duration_s: float
    gravity_mps2: Vector3
    friction: float
    restitution: float


@dataclass(frozen=True)
class CadScene:
    scene_id: str
    provenance: SyntheticProvenance
    materials: tuple[MaterialSpec, ...]
    bodies: tuple[BoxBody, ...]
    animation: tuple[AnimationKey, ...]
    physics: PhysicsSceneSpec


@dataclass(frozen=True)
class ExportArtifact:
    filename: str
    media_type: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class CadExportResult:
    scene_id: str
    status: EvidenceStatus
    artifacts: tuple[ExportArtifact, ...]
    external_tool_execution_performed: bool = False
    physical_validation_performed: bool = False
    fabrication_release: bool = False
    synthetic_notice: str = SYNTHETIC_NOTICE_ID


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise ConfigError(f"{name} must match [a-z][a-z0-9_]*")
    return value


def _vector(value: Any, name: str) -> Vector3:
    data = _mapping(value, name)
    _keys(data, {"x_m", "y_m", "z_m"}, set(), name)
    return Vector3(
        _number(data, "x_m", name),
        _number(data, "y_m", name),
        _number(data, "z_m", name),
    )


def _validate_vector(value: Vector3, name: str) -> None:
    if not isinstance(value, Vector3):
        raise ConfigError(f"{name} must be Vector3")
    _finite(value.x_m, f"{name}.x_m")
    _finite(value.y_m, f"{name}.y_m")
    _finite(value.z_m, f"{name}.z_m")


def _color(value: Any, name: str) -> Color:
    data = _mapping(value, name)
    _keys(data, {"red", "green", "blue", "alpha"}, set(), name)
    return Color(*(_number(data, channel, name, 0, 1) for channel in ("red", "green", "blue", "alpha")))


def _validate_color(color: Color, name: str) -> None:
    if not isinstance(color, Color):
        raise ConfigError(f"{name} must be Color")
    for channel in ("red", "green", "blue", "alpha"):
        bounded_fraction(getattr(color, channel), f"{name}.{channel}")


def _material(value: Any, name: str) -> MaterialSpec:
    data = _mapping(value, name)
    _keys(data, {"materialId", "diffuse", "metallic", "roughness"}, set(), name)
    return MaterialSpec(
        _identifier(data["materialId"], f"{name}.materialId"),
        _color(data["diffuse"], f"{name}.diffuse"),
        _number(data, "metallic", name, 0, 1),
        _number(data, "roughness", name, 0, 1),
    )


def _validate_material(material: MaterialSpec, name: str) -> None:
    if not isinstance(material, MaterialSpec):
        raise ConfigError(f"{name} must be MaterialSpec")
    _identifier(material.material_id, f"{name}.material_id")
    _validate_color(material.diffuse, f"{name}.diffuse")
    bounded_fraction(material.metallic, f"{name}.metallic")
    bounded_fraction(material.roughness, f"{name}.roughness")


def _enum_member(enum_type: Any, value: Any, name: str) -> Any:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        choices = ", ".join(member.value for member in enum_type)
        raise ConfigError(f"{name} must be one of {choices}") from exc


def _body(value: Any, name: str) -> BoxBody:
    data = _mapping(value, name)
    required = {"bodyId", "kind", "center_m", "size_m", "yaw_rad", "mass_kg", "physicsMode", "materialId"}
    _keys(data, required, set(), name)
    return BoxBody(
        _identifier(data["bodyId"], f"{name}.bodyId"),
        _enum_member(CadBodyKind, data["kind"], f"{name}.kind"),
        _vector(data["center_m"], f"{name}.center_m"),
        _vector(data["size_m"], f"{name}.size_m"),
        _number(data, "yaw_rad", name),
        _number(data, "mass_kg", name, 0, strict_low=True),
        _enum_member(PhysicsBodyMode, data["physicsMode"], f"{name}.physicsMode"),
        _identifier(data["materialId"], f"{name}.materialId"),
    )


def _validate_body(body: BoxBody, name: str = "body") -> None:
    if not isinstance(body, BoxBody):
        raise ConfigError(f"{name} must be BoxBody")
    _identifier(body.body_id, f"{name}.body_id")
    if not isinstance(body.kind, CadBodyKind) or not isinstance(body.physics_mode, PhysicsBodyMode):
        raise ConfigError(f"{name} kind and physics_mode must use their declared enums")
    _validate_vector(body.center_m, f"{name}.center_m")
    _validate_vector(body.size_m, f"{name}.size_m")
    _at_least(body.size_m.x_m, 0, f"{name}.size_m.x_m", strict=True)
    _at_least(body.size_m.y_m, 0, f"{name}.size_m.y_m", strict=True)
    _at_least(body.size_m.z_m, 0, f"{name}.size_m.z_m", strict=True)
    _finite(body.yaw_rad, f"{name}.yaw_rad")
    _at_least(body.mass_kg, 0, f"{name}.mass_kg", strict=True)
    _identifier(body.material_id, f"{name}.material_id")


def _animation(value: Any, name: str) -> AnimationKey:
    data = _mapping(value, name)
    _keys(data, {"bodyId", "time_s", "translation_m", "yaw_rad", "interpolation"}, set(), name)
    return AnimationKey(
        _identifier(data["bodyId"], f"{name}.bodyId"),
        _number(data, "time_s", name, 0),
        _vector(data["translation_m"], f"{name}.translation_m"),
        _number(data, "yaw_rad", name),
        _enum_member(AnimationInterpolation, data["interpolation"], f"{name}.interpolation"),
    )


def _physics(value: Any) -> PhysicsSceneSpec:
    data = _mapping(value, "physics")
    _keys(data, {"timestep_s", "duration_s", "gravity_mps2", "friction", "restitution"}, set(), "physics")
    return PhysicsSceneSpec(
        _number(data, "timestep_s", "physics", 0, strict_low=True),
        _number(data, "duration_s", "physics", 0),
        _vector(data["gravity_mps2"], "physics.gravity_mps2"),
        _number(data, "friction", "physics", 0),
        _number(data, "restitution", "physics", 0, 1),
    )


def _validate_physics(physics: PhysicsSceneSpec) -> None:
    if not isinstance(physics, PhysicsSceneSpec):
        raise ConfigError("physics must be PhysicsSceneSpec")
    _at_least(physics.timestep_s, 0, "physics.timestep_s", strict=True)
    _at_least(physics.duration_s, 0, "physics.duration_s")
    _validate_vector(physics.gravity_mps2, "physics.gravity_mps2")
    if physics.gravity_mps2.x_m != 0 or physics.gravity_mps2.y_m != 0 or physics.gravity_mps2.z_m >= 0:
        raise ConfigError("physics.gravity_mps2 must have zero x/y and negative z")
    _at_least(physics.friction, 0, "physics.friction")
    bounded_fraction(physics.restitution, "physics.restitution")


def _world_extents(body: BoxBody) -> tuple[float, float, float, float, float, float]:
    half_x, half_y = body.size_m.x_m / 2, body.size_m.y_m / 2
    cosine, sine = math.cos(body.yaw_rad), math.sin(body.yaw_rad)
    extent_x = abs(cosine) * half_x + abs(sine) * half_y
    extent_y = abs(sine) * half_x + abs(cosine) * half_y
    return (
        body.center_m.x_m - extent_x, body.center_m.x_m + extent_x,
        body.center_m.y_m - extent_y, body.center_m.y_m + extent_y,
        body.center_m.z_m - body.size_m.z_m / 2, body.center_m.z_m + body.size_m.z_m / 2,
    )


def _boxes_overlap(left: BoxBody, right: BoxBody) -> bool:
    a, b = _world_extents(left), _world_extents(right)
    return all(a[2 * axis] < b[2 * axis + 1] and b[2 * axis] < a[2 * axis + 1] for axis in range(3))


def _validate_scene(scene: CadScene) -> None:
    if not isinstance(scene, CadScene):
        raise ConfigError("scene must be CadScene")
    _identifier(scene.scene_id, "scene.scene_id")
    _validate_provenance(scene.provenance, "scene.provenance")
    if not isinstance(scene.materials, tuple) or not scene.materials:
        raise ConfigError("scene.materials must be a non-empty tuple")
    material_ids = []
    for index, material in enumerate(scene.materials):
        _validate_material(material, f"scene.materials[{index}]")
        if material.material_id in material_ids:
            raise ConfigError(f"duplicate material ID {material.material_id}")
        material_ids.append(material.material_id)
    if not isinstance(scene.bodies, tuple) or not scene.bodies:
        raise ConfigError("scene.bodies must be a non-empty tuple")
    bodies_by_id = {}
    for index, body in enumerate(scene.bodies):
        _validate_body(body, f"scene.bodies[{index}]")
        if body.body_id in bodies_by_id:
            raise ConfigError(f"duplicate body ID {body.body_id}")
        if body.material_id not in material_ids:
            raise ConfigError(f"body {body.body_id} references unknown material {body.material_id}")
        bodies_by_id[body.body_id] = body
    if not any(body.kind is CadBodyKind.MACHINE for body in scene.bodies):
        raise ConfigError("scene requires at least one MACHINE body for OCE-CTL-01")
    bunkers = [body for body in scene.bodies if body.kind is CadBodyKind.BUNKER]
    if not bunkers:
        raise ConfigError("scene requires at least one BUNKER body for BUNKER-01")
    for body in scene.bodies:
        if body.physics_mode is PhysicsBodyMode.RIGID and any(_boxes_overlap(body, bunker) for bunker in bunkers):
            raise ConfigError(f"rigid body {body.body_id} overlaps the prohibited bunker interior envelope")
    _validate_physics(scene.physics)
    if not isinstance(scene.animation, tuple):
        raise ConfigError("scene.animation must be a tuple")
    series: dict[str, list[AnimationKey]] = {}
    for index, key in enumerate(scene.animation):
        if not isinstance(key, AnimationKey):
            raise ConfigError(f"scene.animation[{index}] must be AnimationKey")
        _identifier(key.body_id, f"scene.animation[{index}].body_id")
        _at_least(key.time_s, 0, f"scene.animation[{index}].time_s")
        _validate_vector(key.translation_m, f"scene.animation[{index}].translation_m")
        _finite(key.yaw_rad, f"scene.animation[{index}].yaw_rad")
        if not isinstance(key.interpolation, AnimationInterpolation):
            raise ConfigError(f"scene.animation[{index}].interpolation is invalid")
        body = bodies_by_id.get(key.body_id)
        if body is None:
            raise ConfigError(f"animation references unknown body {key.body_id}")
        if body.physics_mode is PhysicsBodyMode.STATIC:
            raise ConfigError(f"animation body {key.body_id} must be RIGID or KINEMATIC")
        if key.time_s > scene.physics.duration_s:
            raise ConfigError(f"animation body {key.body_id} exceeds physics.duration_s")
        series.setdefault(key.body_id, []).append(key)
    for body_id, keys in series.items():
        if keys[0].time_s != 0:
            raise ConfigError(f"animation series {body_id} must start at time zero")
        if any(right.time_s <= left.time_s for left, right in zip(keys, keys[1:])):
            raise ConfigError(f"animation series {body_id} times must be strictly increasing")


def _reject_location_keys(value: Any, path: str = "cad") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"(?<!^)(?=[A-Z])", "_", str(key)).lower()
            tokens = set(normalized.split("_"))
            forbidden = {
                "latitude", "longitude", "gps", "gnss", "geohash", "address", "street",
                "postcode", "zip", "apn", "assessor", "parcel", "geolocation",
            }
            if normalized in {"lat", "lon", "plus_code", "parcel_id", "real_property_id"} or tokens & forbidden:
                raise ConfigError(f"{path}.{key} is prohibited; CAD scenes accept local relative coordinates only")
            _reject_location_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_location_keys(item, f"{path}[{index}]")


def parse_cad_scene(data: dict[str, Any]) -> CadScene:
    _reject_location_keys(data)
    _mapping(data, "cad")
    required = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "scope", "unitSystem",
        "coordinateConvention", "sceneId", "provenance", "materials", "bodies", "animation", "physics",
    }
    _keys(data, required, set(), "cad")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": "1.0.0",
        "platform": "OCE-CTL-01",
        "scope": "BUNKER-01",
        "unitSystem": "SI",
        "coordinateConvention": COORDINATE_CONVENTION_ID,
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"cad.{key} must be {expected}")
    raw_materials, raw_bodies, raw_animation = data["materials"], data["bodies"], data["animation"]
    if not isinstance(raw_materials, list) or not raw_materials:
        raise ConfigError("cad.materials must be a non-empty array")
    if not isinstance(raw_bodies, list) or not raw_bodies:
        raise ConfigError("cad.bodies must be a non-empty array")
    if not isinstance(raw_animation, list):
        raise ConfigError("cad.animation must be an array")
    scene = CadScene(
        scene_id=_identifier(data["sceneId"], "cad.sceneId"),
        provenance=_parse_provenance(data["provenance"], "cad.provenance"),
        materials=tuple(_material(item, f"cad.materials[{index}]") for index, item in enumerate(raw_materials)),
        bodies=tuple(_body(item, f"cad.bodies[{index}]") for index, item in enumerate(raw_bodies)),
        animation=tuple(_animation(item, f"cad.animation[{index}]") for index, item in enumerate(raw_animation)),
        physics=_physics(data["physics"]),
    )
    _validate_scene(scene)
    return scene


def load_cad_scene(path: str | Path) -> CadScene:
    return parse_cad_scene(load_json(path))


def mesh_box(body: BoxBody) -> MeshObject:
    """Return a closed, yaw-rotated, outward-wound box in right-handed metres."""

    _validate_body(body)
    hx, hy, hz = body.size_m.x_m / 2, body.size_m.y_m / 2, body.size_m.z_m / 2
    cosine, sine = math.cos(body.yaw_rad), math.sin(body.yaw_rad)
    local = (
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    )
    vertices = tuple(Vector3(
        _sum((body.center_m.x_m, _product(x, cosine, name="rotated x"), -_product(y, sine, name="rotated x")),
             "vertex x"),
        _sum((body.center_m.y_m, _product(x, sine, name="rotated y"), _product(y, cosine, name="rotated y")),
             "vertex y"),
        _sum((body.center_m.z_m, z), "vertex z"),
    ) for x, y, z in local)
    triangles = (
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    )
    for triangle in triangles:
        a, b, c = (vertices[index] for index in triangle)
        ab = (b.x_m - a.x_m, b.y_m - a.y_m, b.z_m - a.z_m)
        ac = (c.x_m - a.x_m, c.y_m - a.y_m, c.z_m - a.z_m)
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        area_squared = _sum((component * component for component in cross), "triangle area squared")
        if area_squared <= 0:
            raise ConfigError(f"body {body.body_id} contains a degenerate triangle")
    return MeshObject(body, vertices, triangles)


def _fmt(value: float) -> str:
    text = repr(_finite(value, "generated numeric value"))
    return text[:-2] if text.endswith(".0") else text


def export_wavefront(scene: CadScene) -> tuple[str, str]:
    _validate_scene(scene)
    obj_lines = [
        "# Synthetic OCE-CTL-01 / BUNKER-01 scene; local metres; unreviewed.",
        "mtllib scene.mtl",
    ]
    vertex_offset = 1
    for body in scene.bodies:
        mesh = mesh_box(body)
        obj_lines.extend((f"o {body.body_id}", f"usemtl {body.material_id}", "s off"))
        obj_lines.extend(f"v {vertex.x_m:.6f} {vertex.y_m:.6f} {vertex.z_m:.6f}" for vertex in mesh.vertices_m)
        obj_lines.extend(
            f"f {a + vertex_offset} {b + vertex_offset} {c + vertex_offset}" for a, b, c in mesh.triangles
        )
        vertex_offset += len(mesh.vertices_m)
    mtl_lines = ["# Synthetic materials; no external texture assets."]
    for material in scene.materials:
        color = material.diffuse
        mtl_lines.extend((
            f"newmtl {material.material_id}",
            f"Kd {color.red:.6f} {color.green:.6f} {color.blue:.6f}",
            f"d {color.alpha:.6f}",
            f"# roughness {material.roughness:.6f}",
            f"# metallic {material.metallic:.6f}",
            "illum 2",
        ))
    return "\n".join(obj_lines) + "\n", "\n".join(mtl_lines) + "\n"


def generate_blender_python(scene: CadScene) -> str:
    _validate_scene(scene)
    materials = tuple(
        (item.material_id, (item.diffuse.red, item.diffuse.green, item.diffuse.blue, item.diffuse.alpha),
         item.metallic, item.roughness)
        for item in scene.materials
    )
    body_centers = tuple(
        (body.body_id, (body.center_m.x_m, body.center_m.y_m, body.center_m.z_m))
        for body in scene.bodies
    )
    meshes = []
    for body in scene.bodies:
        mesh = mesh_box(body)
        hx, hy, hz = body.size_m.x_m / 2, body.size_m.y_m / 2, body.size_m.z_m / 2
        local_vertices = (
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
        )
        meshes.append((
            body.body_id, body.physics_mode.value, body.material_id, body.yaw_rad,
            local_vertices, mesh.triangles,
        ))
    animation = tuple(
        (key.body_id, key.time_s, (key.translation_m.x_m, key.translation_m.y_m, key.translation_m.z_m),
         key.yaw_rad, key.interpolation.value)
        for key in scene.animation
    )
    # Keep optional framework imports out of this core module's import table/source.
    framework_import = "import " + "bpy"
    return f"""# Generated synthetic scene. Run manually with Blender 4.x only.
{framework_import}
import math
import os

if not 4 <= bpy.app.version[0] < 5:
    raise RuntimeError("This generated scene requires Blender 4.x")

SCENE_ID = {scene.scene_id!r}
TIMESTEP_S = {scene.physics.timestep_s!r}
DURATION_S = {scene.physics.duration_s!r}
MATERIALS = {materials!r}
BODIES = {body_centers!r}
MESHES = {meshes!r}
ANIMATION = {animation!r}

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.fps = 24
scene.render.fps_base = 24.0 * TIMESTEP_S
scene.frame_start = 1
scene.frame_end = 1 + int(round(DURATION_S / TIMESTEP_S))
scene.gravity = (0.0, 0.0, {scene.physics.gravity_mps2.z_m!r})

for material_id, rgba, metallic, roughness in MATERIALS:
    material = bpy.data.materials.new(material_id)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Alpha"].default_value = rgba[3]
    material.diffuse_color = rgba

objects = {{}}
initial_locations = dict(BODIES)
bpy.ops.object.select_all(action="DESELECT")
for body_id, mode, material_id, yaw, vertices, faces in MESHES:
    mesh = bpy.data.meshes.new(body_id + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(body_id, mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(bpy.data.materials[material_id])
    obj.location = initial_locations[body_id]
    obj.rotation_euler = (0.0, 0.0, yaw)
    obj["physics_mode"] = mode
    obj["synthetic_unreviewed"] = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = "ACTIVE" if mode == "RIGID" else "PASSIVE"
    obj.rigid_body.collision_shape = "BOX"
    obj.rigid_body.kinematic = mode == "KINEMATIC"
    obj.rigid_body.friction = {scene.physics.friction!r}
    obj.rigid_body.restitution = {scene.physics.restitution!r}
    obj.select_set(False)
    objects[body_id] = obj

for body_id, time_s, translation, yaw, interpolation in ANIMATION:
    obj = objects[body_id]
    frame = 1 + int(round(time_s / TIMESTEP_S))
    obj.location = translation
    obj.rotation_euler.z = yaw
    obj.keyframe_insert(data_path="location", frame=frame)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    action = obj.animation_data.action
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            if abs(point.co.x - frame) < 1e-6:
                point.interpolation = interpolation

scene.frame_set(1)
output_path = os.environ.get("OCE_BLENDER_OUTPUT")
if output_path:
    bpy.ops.wm.save_mainfile(filepath=os.path.abspath(output_path))
"""


def generate_mujoco_mjcf(scene: CadScene) -> str:
    _validate_scene(scene)
    lines = [
        f'<mujoco model="{escape(scene.scene_id, quote=True)}">',
        '  <compiler angle="radian" coordinate="local"/>',
        (f'  <option timestep="{_fmt(scene.physics.timestep_s)}" gravity="'
         f'{_fmt(scene.physics.gravity_mps2.x_m)} {_fmt(scene.physics.gravity_mps2.y_m)} '
         f'{_fmt(scene.physics.gravity_mps2.z_m)}"/>'),
        f'  <!-- Synthetic restitution metadata: {_fmt(scene.physics.restitution)}; not calibrated contact physics. -->',
        "  <default>",
        f'    <geom friction="{_fmt(scene.physics.friction)} 0.005 0.0001" condim="3"/>',
        "  </default>",
        "  <asset>",
    ]
    for material in scene.materials:
        color = material.diffuse
        lines.append(
            f'    <material name="{material.material_id}" rgba="{_fmt(color.red)} {_fmt(color.green)} '
            f'{_fmt(color.blue)} {_fmt(color.alpha)}" metallic="{_fmt(material.metallic)}" '
            f'roughness="{_fmt(material.roughness)}"/>'
        )
    lines.extend(("  </asset>", "  <worldbody>",
                  '    <geom name="ground" type="plane" pos="0 0 0" size="100 100 0.1" rgba="0.3 0.3 0.3 1"/>'))
    for body in scene.bodies:
        center, size = body.center_m, body.size_m
        attributes = ""
        if body.physics_mode is PhysicsBodyMode.KINEMATIC:
            attributes = ' mocap="true"'
        lines.append(
            f'    <body name="{body.body_id}" pos="{_fmt(center.x_m)} {_fmt(center.y_m)} {_fmt(center.z_m)}" '
            f'euler="0 0 {_fmt(body.yaw_rad)}"{attributes}>'
        )
        lines.append(f'      <!-- kind={body.kind.value}; physicsMode={body.physics_mode.value}; synthetic initial pose. -->')
        if body.physics_mode is PhysicsBodyMode.RIGID:
            lines.append("      <freejoint/>")
        try:
            inertia = (
                body.mass_kg * (size.y_m ** 2 + size.z_m ** 2) / 12.0,
                body.mass_kg * (size.x_m ** 2 + size.z_m ** 2) / 12.0,
                body.mass_kg * (size.x_m ** 2 + size.y_m ** 2) / 12.0,
            )
        except OverflowError as exc:
            raise ConfigError(f"body {body.body_id} produced invalid inertia") from exc
        if any(not math.isfinite(value) or value <= 0 for value in inertia):
            raise ConfigError(f"body {body.body_id} produced invalid inertia")
        lines.append(
            f'      <inertial pos="0 0 0" mass="{_fmt(body.mass_kg)}" diaginertia="'
            f'{_fmt(inertia[0])} {_fmt(inertia[1])} {_fmt(inertia[2])}"/>'
        )
        lines.append(
            f'      <geom name="{body.body_id}_geom" type="box" size="{_fmt(size.x_m / 2)} '
            f'{_fmt(size.y_m / 2)} {_fmt(size.z_m / 2)}" material="{body.material_id}"/>'
        )
        lines.append("    </body>")
    for key in scene.animation:
        comment = (f"animation {key.body_id} time_s={_fmt(key.time_s)} translation_m="
                   f"{_fmt(key.translation_m.x_m)},{_fmt(key.translation_m.y_m)},{_fmt(key.translation_m.z_m)} "
                   f"yaw_rad={_fmt(key.yaw_rad)} interpolation={key.interpolation.value}")
        lines.append(f"    <!-- {comment} -->")
    lines.extend(("  </worldbody>", "</mujoco>"))
    return "\n".join(lines) + "\n"


def generate_openscad(scene: CadScene) -> str:
    _validate_scene(scene)
    lines = [
        "// Synthetic local scene in millimetres; visualization only; not fabrication CAD.",
        "$fn = 24;",
    ]
    material_by_id = {item.material_id: item for item in scene.materials}
    for body in scene.bodies:
        material = material_by_id[body.material_id]
        color = material.diffuse
        lines.extend((
            f"// {body.body_id}: kind={body.kind.value}; physicsMode={body.physics_mode.value}; mass_kg={_fmt(body.mass_kg)}",
            f"{body.body_id}_center_mm = [{_fmt(body.center_m.x_m * 1000)}, {_fmt(body.center_m.y_m * 1000)}, {_fmt(body.center_m.z_m * 1000)}];",
            f"{body.body_id}_size_mm = [{_fmt(body.size_m.x_m * 1000)}, {_fmt(body.size_m.y_m * 1000)}, {_fmt(body.size_m.z_m * 1000)}];",
            f"{body.body_id}_yaw_deg = {_fmt(math.degrees(body.yaw_rad))};",
            f"module {body.body_id}(center_mm={body.body_id}_center_mm, size_mm={body.body_id}_size_mm, yaw_deg={body.body_id}_yaw_deg) {{",
            f"  color([{_fmt(color.red)}, {_fmt(color.green)}, {_fmt(color.blue)}, {_fmt(color.alpha)}])",
            "    translate(center_mm) rotate([0, 0, yaw_deg]) cube(size_mm, center=true);",
            "}",
            f"{body.body_id}();",
        ))
    return "\n".join(lines) + "\n"


def generate_freecad_python(scene: CadScene) -> str:
    _validate_scene(scene)
    bodies = tuple(
        (body.body_id, body.kind.value, body.physics_mode.value,
         (body.center_m.x_m * 1000, body.center_m.y_m * 1000, body.center_m.z_m * 1000),
         (body.size_m.x_m * 1000, body.size_m.y_m * 1000, body.size_m.z_m * 1000),
         math.degrees(body.yaw_rad), body.mass_kg, body.material_id)
        for body in scene.bodies
    )
    materials = tuple(
        (item.material_id, (item.diffuse.red, item.diffuse.green, item.diffuse.blue), item.diffuse.alpha)
        for item in scene.materials
    )
    framework_import = "import " + "FreeCAD as App"
    return f"""# Generated synthetic scene in millimetres. Run manually inside FreeCAD only.
{framework_import}
import math

SCENE_ID = {scene.scene_id!r}
BODIES = {bodies!r}
MATERIALS = dict({materials!r})

doc = App.newDocument(SCENE_ID)
for body_id, kind, mode, center_mm, size_mm, yaw_deg, mass_kg, material_id in BODIES:
    obj = doc.addObject("Part::Box", body_id)
    obj.Label = body_id
    obj.Length = size_mm[0]
    obj.Width = size_mm[1]
    obj.Height = size_mm[2]
    rotation = App.Rotation(App.Vector(0, 0, 1), yaw_deg)
    offset = rotation.multVec(App.Vector(-size_mm[0] / 2, -size_mm[1] / 2, -size_mm[2] / 2))
    obj.Placement = App.Placement(App.Vector(*center_mm) + offset, rotation)
    obj.addProperty("App::PropertyString", "OCEKind", "Synthetic metadata")
    obj.OCEKind = kind
    obj.addProperty("App::PropertyString", "OCEPhysicsMode", "Synthetic metadata")
    obj.OCEPhysicsMode = mode
    obj.addProperty("App::PropertyFloat", "OCEMass_kg", "Synthetic metadata")
    obj.OCEMass_kg = mass_kg
    rgb, alpha = MATERIALS[material_id]
    obj.ViewObject.ShapeColor = rgb
    obj.ViewObject.Transparency = int(round((1.0 - alpha) * 100))
doc.recompute()
"""


def external_tool_report() -> dict[str, str | None]:
    """Report executable paths only; never execute or infer validation from them."""

    return {
        "blender": shutil.which("blender"),
        "openscad": shutil.which("openscad"),
        "freecadcmd": shutil.which("freecadcmd") or shutil.which("FreeCADCmd"),
        "python": shutil.which("python") or shutil.which("python3"),
    }


def export_scene(scene: CadScene, output_dir: str | Path) -> CadExportResult:
    """Generate and stage all six fixed artifacts before replacing destination files."""

    obj, mtl = export_wavefront(scene)
    generated = (
        ("scene.obj", "model/obj", obj),
        ("scene.mtl", "model/mtl", mtl),
        ("blender_scene.py", "text/x-python", generate_blender_python(scene)),
        ("ctl01_bunker_physics.xml", "application/xml", generate_mujoco_mjcf(scene)),
        ("scene.scad", "text/plain", generate_openscad(scene)),
        ("scene_freecad.py", "text/x-python", generate_freecad_python(scene)),
    )
    payloads = tuple((filename, media_type, text.encode("utf-8")) for filename, media_type, text in generated)
    destination = Path(output_dir)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise OSError(f"CAD output destination is a symlink or not a directory: {destination}")
    for filename, _, _ in payloads:
        path = destination / filename
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise OSError(f"CAD artifact destination is a symlink or not a regular file: {path}")
    destination.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for filename, _, payload in payloads:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".oce-cad-", suffix=".tmp", dir=destination)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
            staged.append((temporary, destination / filename))
        for temporary, final in staged:
            os.replace(temporary, final)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
    artifacts = tuple(
        ExportArtifact(filename, media_type, hashlib.sha256(payload).hexdigest(), len(payload))
        for filename, media_type, payload in payloads
    )
    return CadExportResult(scene.scene_id, EvidenceStatus.SIMULATED_UNREVIEWED, artifacts)


def cad_export_result_json(result: CadExportResult) -> str:
    if not isinstance(result, CadExportResult):
        raise ConfigError("result must be CadExportResult")
    if (result.status != EvidenceStatus.SIMULATED_UNREVIEWED
            or result.external_tool_execution_performed is not False
            or result.physical_validation_performed is not False
            or result.fabrication_release is not False):
        raise ConfigError("CAD results must remain simulated, unreviewed, unexecuted externally, and unreleased")
    if tuple(artifact.filename for artifact in result.artifacts) != ARTIFACT_FILENAMES:
        raise ConfigError("CAD result artifacts must contain the six fixed filenames in canonical order")
    return json.dumps(_json_compatible(result), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def write_cad_export_result(result: CadExportResult, output_dir: str | Path) -> Path:
    text = cad_export_result_json(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class CadExporter:
    """Stateless convenience facade over the pure generators and atomic writer."""

    def export(self, scene: CadScene, output_dir: str | Path) -> CadExportResult:
        return export_scene(scene, output_dir)

    @staticmethod
    def wavefront(scene: CadScene) -> tuple[str, str]:
        return export_wavefront(scene)

    @staticmethod
    def blender(scene: CadScene) -> str:
        return generate_blender_python(scene)

    @staticmethod
    def mujoco(scene: CadScene) -> str:
        return generate_mujoco_mjcf(scene)

    @staticmethod
    def openscad(scene: CadScene) -> str:
        return generate_openscad(scene)

    @staticmethod
    def freecad(scene: CadScene) -> str:
        return generate_freecad_python(scene)
