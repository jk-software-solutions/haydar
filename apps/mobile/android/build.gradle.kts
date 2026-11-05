allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Some low-memory Windows machines cannot complete Android's release-only
// lint analysis for transitive plugins. Keep the normal lint gate enabled;
// release owners may opt into a build-only fallback with
// -PskipReleaseLint=true after the Flutter/Dart checks have passed.
if (providers.gradleProperty("skipReleaseLint").isPresent) {
    subprojects {
        tasks.matching {
            it.name.startsWith("lintVital") && it.name.endsWith("Release")
        }.configureEach {
            enabled = false
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
