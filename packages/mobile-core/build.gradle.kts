plugins {
    kotlin("multiplatform") version "1.9.22"
    id("com.android.library")
    id("app.cash.sqldelight") version "2.0.1"
    kotlin("plugin.serialization") version "1.9.22"
}

kotlin {
    androidTarget {
        compilations.all {
            kotlinOptions {
                jvmTarget = "17"
            }
        }
    }

    listOf(
        iosX64(),
        iosArm64(),
        iosSimulatorArm64()
    ).forEach {
        it.binaries.framework {
            baseName = "PermiaCore"
            isStatic = true
        }
    }

    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-core:2.3.7")
                implementation("io.ktor:ktor-client-content-negotiation:2.3.7")
                implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.7")
                implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.2")
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
                implementation("app.cash.sqldelight:runtime:2.0.1")
                implementation("app.cash.sqldelight:coroutines-extensions:2.0.1")
                implementation("org.jetbrains.kotlinx:kotlinx-datetime:0.5.0")
            }
        }

        val androidMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-okhttp:2.3.7")
                implementation("app.cash.sqldelight:android-driver:2.0.1")
            }
        }

        val iosMain by creating {
            dependsOn(commonMain)
            dependencies {
                implementation("io.ktor:ktor-client-darwin:2.3.7")
                implementation("app.cash.sqldelight:native-driver:2.0.1")
            }
        }
    }
}

android {
    namespace = "is.permia.core"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

sqldelight {
    databases {
        create("PermiaDatabase") {
            packageName.set("is.permia.core.db")
            srcDirs.setFrom("src/commonMain/sqldelight")
        }
    }
}
