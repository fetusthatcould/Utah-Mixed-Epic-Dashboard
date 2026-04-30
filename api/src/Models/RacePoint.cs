namespace Ume.Intelligence.Api.Models;

public class RacePoint
{
    public int PointOrder { get; set; }
    public double ElevationM { get; set; }
    public double SlopePctSmooth { get; set; }
    public int TechScore { get; set; }
    public string LandCoverType { get; set; } = string.Empty;
    public double CumulativeFatigueIndex { get; set; }
    public double FoodScore { get; set; }
    public double WaterScore { get; set; }
    
    // We send the geometry as a GeoJSON string for Mapbox
    public string GeoJson { get; set; } = string.Empty;

    // Adding Road surface type and trail names
    public string? RoadSurface { get; set; }
    public string? TrailName { get; set; }
    public bool IsSingletrack { get; set; }
}